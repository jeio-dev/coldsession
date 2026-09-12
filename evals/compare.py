#!/usr/bin/env python3
"""Opt-in, budgeted paired evaluations of direct, baseline, and current workflows.

Scenario JSON supplies project files, task, writable files, immutable external
checks, and optional fixture review oracle. All arms receive identical source.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import lib


def load_runtime(source):
    loader = importlib.machinery.SourceFileLoader('comparison_runtime', str(source / 'bin/plan'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    rt = importlib.util.module_from_spec(spec)
    loader.exec_module(rt)
    return rt


def put(root, name, text):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('scenario path escapes project')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def workflow(source, project, scenario, improved):
    # Fixtures intentionally model an already human-approved task. This is
    # evaluation setup, never an installer side effect or production approval.
    for folder in ('commands', 'bin', 'hooks'):
        for path in (source / folder).glob('*'):
            if path.is_file():
                dest = project / '.claude' / folder / path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    fmt = '2.0.0' if improved else '1.5.0'
    text = ('---\nphase: 01-eval\nrev: 1\nstatus: approved\nreviewed: 1\nready: 1\n'
            f'workflow-rev: {fmt}\ntasks:\n'
            f"  T1: {{deps: [], status: pending, files: [{', '.join(scenario['writable'])}]}}\n---\n\n"
            '# Evaluation fixture\n\n## T1 - task\n\nGoal: ' + scenario['task'] + '\n'
            'Deliverables: ' + ', '.join(scenario['writable']) + '\n'
            'Acceptance Criteria: ' + scenario['acceptance'] + '\n'
            + '\n'.join('Verify: `' + command + '` exits 0' for command in scenario['verify'])
            + '\n\n## Constraints\n\n' + scenario.get('constraints', 'Preserve existing behavior outside this task.')
            + '\n\n## Findings\n\n## Changelog\n')
    put(project, 'PLAN.md', '---\ncurrent: docs/plans/01-eval.md\n---\n- [ ] docs/plans/01-eval.md\n')
    put(project, 'docs/plans/01-eval.md', text)
    if improved:
        rt = load_runtime(source)
        rt.ROOT = str(project)
        phase = rt.read_phase(str(project / 'docs/plans/01-eval.md'))
        fingerprint = rt.specification(phase)
        put(project, 'docs/plans/01-eval.md', rt.set_metas(text, {'ready-spec': fingerprint, 'reviewed-spec': fingerprint}))
    # Explicit harness config supplied by the scenario, identical permissions in
    # each arm. Hook differences are the treatment, and recorded in the report.
    settings = dict(scenario.get('settings', {}))
    if improved:
        loader = importlib.machinery.SourceFileLoader('comparison_install', str(source / 'bin/cs_install.py'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        installer = importlib.util.module_from_spec(spec)
        loader.exec_module(installer)
        import os
        settings['hooks'] = installer.configured_hooks(os.name == 'nt')
    else:
        # Baseline's four published hook wrappers, without inherited plugins.
        import os
        suffix = 'cmd' if os.name == 'nt' else 'sh'
        settings['hooks'] = {}
        for event, kind, matcher in [('UserPromptSubmit', 'stage', None), ('PreToolUse', 'read', 'Read|Edit|Write'),
                                      ('PreToolUse', 'write', 'Edit|Write'), ('PostToolUse', 'lint', 'Edit|Write')]:
            entry = {'hooks': [{'type': 'command', 'command': f'"{project.as_posix()}/.claude/hooks/cs-guard-{kind}.{suffix}"'}]}
            if matcher:
                entry['matcher'] = matcher
            settings['hooks'].setdefault(event, []).append(entry)
    put(project, '.claude/settings.json', json.dumps(settings))


def run_arm(scenario, arm, baseline, budget, timeout):
    result = {'arm': arm, 'correctness': False, 'regressions': None, 'false_findings': None,
              'unnecessary_changes': None, 'human_interventions': None, 'tokens': None,
              'failures': [], 'budget_usd': budget, 'trace_truncated': False}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='cs-comparison-') as temporary:
        project = Path(temporary)
        for name, text in scenario['files'].items():
            put(project, name, text)
        before = {p: hashlib.sha256((project / p).read_bytes()).hexdigest() for p in scenario['files']}
        source = baseline if arm == 'baseline' else lib.ROOT
        if arm != 'direct':
            workflow(source, project, scenario, arm == 'improved')
        else:
            put(project, '.claude/settings.json', json.dumps(scenario.get('settings', {})))
        prompt = scenario['task'] if arm == 'direct' else '/cs-build T1'
        prompt += '\nAcceptance: ' + scenario['acceptance']
        try:
            events, proc = lib.run_claude(project, prompt, max_budget_usd=budget, timeout=timeout)
            result.update(exit=proc.returncode, timed_out=proc.timed_out, trace_truncated=proc.truncated)
            if proc.returncode or proc.timed_out:
                result['failures'].append('harness failed or timed out: ' + proc.stdout)
            summaries = [e for e in events if e.get('type') == 'result']
            if summaries:
                last = summaries[-1]
                if last.get('is_error'):
                    result['failures'].append('harness reported error: ' + str(last.get('subtype', 'unknown')))
                result['tokens'] = last.get('usage')  # measured harness counts, not estimates
                result['cost_usd'] = last.get('total_cost_usd')
                result['permission_denials'] = last.get('permission_denials', [])
            # Grading code is supplied outside the agent-writable project and run
            # after the session; source tests inside the fixture cannot fake it.
            checks = []
            rt = load_runtime(lib.ROOT)
            rt.ROOT = str(project)
            for code in scenario['checks']:
                grade_env = lib.isolated_env(project)
                grade_env.pop('ANTHROPIC_API_KEY', None)
                checks.append(rt.bounded_run([sys.executable, '-E', '-c', code], shell=False, timeout=30, env=grade_env))
            result['checks'] = checks
            result['regressions'] = sum(c['exit'] != 0 for c in checks)
            result['correctness'] = not result['failures'] and result['regressions'] == 0
            changed = []
            for path in project.rglob('*'):
                if not path.is_file():
                    continue
                relative = path.relative_to(project).as_posix()
                if relative.startswith(('.claude/', '.eval-config/', '.coldsession-state/', 'docs/plans/', '__pycache__/')) or relative == 'PLAN.md':
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() != before.get(relative):
                    changed.append(relative)
            changed += [name for name in before if not (project / name).exists()]
            result['changed_files'] = sorted(set(changed))
            result['unnecessary_changes'] = sorted(set(changed) - set(scenario['writable']))
            result['false_findings'] = 'requires independent human adjudication'
            result['human_interventions'] = 0  # headless run; denials are separately recorded
        except (OSError, ValueError, lib.FixtureError) as exc:
            result['failures'].append(str(exc))
    result['elapsed_seconds'] = time.monotonic() - started
    return lib.redact(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', type=Path)
    parser.add_argument('--baseline', type=Path, required=True, help='unchanged 2.5 release checkout')
    parser.add_argument('--live', action='store_true', help='explicitly authorize paid harness calls')
    parser.add_argument('--budget-usd', type=float, required=True, help='total budget across all three arms')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--output', type=Path, default=Path('comparison.json'))
    args = parser.parse_args()
    if not args.live or args.budget_usd <= 0 or args.timeout < 1:
        parser.error('--live, positive --budget-usd, and a positive timeout are required')
    scenario = json.loads(args.scenario.read_text(encoding='utf-8'))
    report = {'scenario_sha': hashlib.sha256(args.scenario.read_bytes()).hexdigest(),
              'baseline': str(args.baseline.resolve()), 'harness': 'claude',
              'budget_usd': args.budget_usd, 'runs': [],
              'limits': 'One scenario is insufficient for quality claims. False findings need independent adjudication. Includes failed runs.'}
    for arm in ('direct', 'baseline', 'improved'):
        report['runs'].append(run_arm(scenario, arm, args.baseline, args.budget_usd / 3, args.timeout))
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(r['correctness'] for r in report['runs']) else 1


if __name__ == '__main__':
    sys.exit(main())
