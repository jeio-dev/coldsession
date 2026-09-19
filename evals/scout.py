#!/usr/bin/env python3
"""Opt-in, budgeted paired evaluation of scout against native exploration.

Every scenario under evals/scenarios/scout/ names a real revision of this
repository, optional exact patches, one exploration-heavy task, the files the
task may change, and grading code that runs after the session, outside
anything the agent could edit. Each run starts from that revision, committed
into a fresh git repository with coldsession installed. The prompt and the
permissions are identical in every arm; the only treatment is whether
`plan scout setup` ran, and with which model:

    python evals/scout.py --live --accept-data-sharing --budget-usd 20 \\
        --model gemini-3.8-flash-low --model gemini-3.8-flash-high --repeats 2 \\
        --output evals/results/scout-comparison.json
    python evals/scout.py --summarize evals/results/scout-comparison.json

`--accept-data-sharing` is the human accepting scout's disclosure for the
disposable fixture projects: their content goes to the scout provider. The
Claude budget is split equally across runs; provider usage is governed by the
provider's own limits, as in real use. `--prepare-only` builds every project
and grades it unchanged, without calling either model, to check the harness.
"""
import argparse
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SCENARIOS = Path(__file__).resolve().parent / 'scenarios' / 'scout'
SCENARIO_KEYS = {'id', 'derived_from', 'exploration', 'source', 'patches', 'task', 'acceptance', 'writable', 'checks'}
# Paths the harness itself writes; everything else the agent changes is graded.
HARNESS_PATHS = ('.eval-config/', '.coldsession-state/', '.claude/settings.local.json')
MIN_REDUCTION = 0.10
MAX_REJECTION = 0.20


def plan_command():
    return '.claude/bin/plan.cmd' if os.name == 'nt' else '.claude/bin/plan'


def load_scenario(path):
    scenario = json.loads(Path(path).read_text(encoding='utf-8'))
    missing = SCENARIO_KEYS - set(scenario)
    if missing or set(scenario) - SCENARIO_KEYS:
        raise lib.FixtureError(f'{path}: scenario keys must be exactly {sorted(SCENARIO_KEYS)}')
    if not scenario['writable'] or not scenario['checks']:
        raise lib.FixtureError(f'{path}: a scenario needs writable files and checks')
    return scenario


def prompt(scenario):
    """The same words in every arm; they end with the soft rule the workflow commands carry."""
    return (scenario['task'] + '\n\nAcceptance: ' + scenario['acceptance'] + '\n\n'
            f'Before exploring, run `{plan_command()} scout status`, and only if it exits 0, '
            'follow what it prints.')


def allowed_tools(scenario):
    """The same scoped rules in every arm: scout commands and the writable files, nothing else."""
    return ([f'Bash({plan_command()} scout:*)']
            + [f'{tool}({name})' for name in scenario['writable'] for tool in ('Edit', 'Write')])


def git(project, *args, check=True):
    result = subprocess.run(['git', '-c', 'user.name=coldsession eval', '-c', 'user.email=eval@invalid',
                             '-c', 'core.autocrlf=false', *args],
                            cwd=project, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise lib.FixtureError(f"git {' '.join(args)} failed: {result.stderr.strip()[:500]}")
    return result.stdout


def materialize(scenario, project):
    """Extract the scenario's revision of this repository and apply its patches."""
    archive = subprocess.run(['git', 'archive', '--format=tar', scenario['source']['rev']],
                             cwd=lib.ROOT, capture_output=True, check=False)
    if archive.returncode:
        raise lib.FixtureError(f"revision {scenario['source']['rev']} is not available: "
                               f"{archive.stderr.decode('utf-8', 'replace').strip()[:300]}")
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        for member in tar.getmembers():
            if not (member.isfile() or member.isdir()) or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise lib.FixtureError(f'unexpected archive member {member.name}')
        tar.extractall(project)
    for patch in scenario['patches']:
        path = project / patch['file']
        text = path.read_bytes().decode('utf-8')
        if text.count(patch['old']) != 1:
            raise lib.FixtureError(f"patch for {patch['file']} must match exactly once")
        path.write_bytes(text.replace(patch['old'], patch['new']).encode('utf-8'))


def prepare(scenario, project, model, accept, scout_timeout):
    """Build one arm's project; `model` None is the native arm. Returns scout setup output or None."""
    materialize(scenario, project)
    git(project, 'init', '-q')
    lib.install(project, scenario['id'])
    (project / '.git' / 'info').mkdir(exist_ok=True)
    (project / '.git' / 'info' / 'exclude').write_text('.eval-config/\n', encoding='utf-8')
    setup = None
    if model is not None:
        command = [sys.executable, str(project / '.claude' / 'bin' / 'plan'), 'scout', 'setup',
                   '--timeout', str(scout_timeout), '--json'] + (['--model', model] if model else [])
        if accept:
            command.append('--accept-data-sharing')
        ran = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False,
                             env=lib.isolated_env(project), stdin=subprocess.DEVNULL, timeout=120)
        setup = {'exit': ran.returncode, 'output': lib.redact(ran.stdout[-2000:] + ran.stderr[-1000:])}
        if ran.returncode:
            raise lib.FixtureError('scout setup failed: ' + setup['output'])
    git(project, 'add', '-A')
    git(project, 'commit', '-q', '-m', f"eval fixture {scenario['id']}")
    return setup


def changed_files(project):
    out = git(project, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    names, tokens, index = [], out.split('\0'), 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if len(token) > 3:
            names.append(token[3:])
            if token[0] in 'RC':
                names.append(tokens[index])
                index += 1
    return sorted({n for n in names if not n.startswith(HARNESS_PATHS) and '__pycache__/' not in n})


def grade(scenario, project, timeout=60):
    env = lib.isolated_env(project)
    for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'):
        env.pop(key, None)
    checks = []
    for code in scenario['checks']:
        try:
            ran = subprocess.run([sys.executable, '-E', '-c', code], cwd=project, text=True,
                                 capture_output=True, timeout=timeout, env=env, check=False)
            checks.append({'exit': ran.returncode, 'output': lib.redact((ran.stdout + ran.stderr)[-1000:])})
        except subprocess.TimeoutExpired:
            checks.append({'exit': None, 'output': f'timed out after {timeout}s'})
    return checks


def scout_counters(project):
    path = project / '.coldsession-state' / 'scout' / 'stats.json'
    try:
        stats = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    stats.pop('last_check', None)
    return stats


def scout_calls(events):
    calls = {'status': 0, 'run': 0}
    for event in events:
        for block in lib._content_blocks(event):
            if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                command = str((block.get('input') or {}).get('command', ''))
                for kind in calls:
                    if f'scout {kind}' in command:
                        calls[kind] += 1
    return calls


def host_tokens(usage):
    keys = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
    if not isinstance(usage, dict) or not all(isinstance(usage.get(k), int) for k in keys[:2]):
        return None
    return sum(usage.get(k) or 0 for k in keys)


def run_one(scenario, arm, model, budget, timeout, accept, scout_timeout, live):
    result = {'scenario': scenario['id'], 'arm': arm, 'model': model, 'correct': False, 'failures': [],
              'budget_usd': budget, 'tokens': None, 'host_tokens': None, 'cost_usd': None,
              'scout': None, 'scout_calls': None, 'changed_files': None, 'out_of_scope': None}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='cs-scout-eval-') as temporary:
        project = Path(os.path.realpath(temporary))
        try:
            result['scout_setup'] = prepare(scenario, project, model, accept, scout_timeout)
            if live:
                events, proc = lib.run_claude(project, prompt(scenario), max_budget_usd=budget, timeout=timeout,
                                               allowed_tools=allowed_tools(scenario))
                result.update(exit=proc.returncode, timed_out=proc.timed_out, trace_truncated=proc.truncated,
                              agent_seconds=proc.elapsed_seconds, scout_calls=scout_calls(events))
                if proc.returncode or proc.timed_out:
                    result['failures'].append('harness failed or timed out: ' + proc.stdout[-500:])
                summaries = [e for e in events if e.get('type') == 'result']
                if summaries:
                    last = summaries[-1]
                    if last.get('is_error'):
                        result['failures'].append('harness reported error: ' + str(last.get('subtype', 'unknown')))
                    result['tokens'] = last.get('usage')  # measured by the harness, never estimated
                    result['host_tokens'] = host_tokens(last.get('usage'))
                    result['cost_usd'] = last.get('total_cost_usd')
                    result['permission_denials'] = last.get('permission_denials', [])
            result['scout'] = scout_counters(project)
            result['changed_files'] = changed_files(project)
            result['out_of_scope'] = sorted(set(result['changed_files']) - set(scenario['writable']))
            result['checks'] = grade(scenario, project)
            result['correct'] = (live and not result['failures']
                                 and all(check['exit'] == 0 for check in result['checks']))
        except (OSError, ValueError, subprocess.SubprocessError, lib.FixtureError) as exc:
            result['failures'].append(str(exc)[:2000])
    result['elapsed_seconds'] = time.monotonic() - started
    return lib.redact(result)


def _median(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(values) if values else None


def summarize(report, min_reduction=MIN_REDUCTION, max_rejection=MAX_REJECTION):
    """Per-arm totals and the issue's decision rule. Unknown measurements stay unknown."""
    runs = report['runs']
    arms = {}
    for run in runs:
        arms.setdefault(run['arm'], []).append(run)
    native = {}
    for run in arms.get('native', []):
        native.setdefault(run['scenario'], []).append(run.get('host_tokens'))
    summary = {'thresholds': {'min_reduction': min_reduction, 'max_rejection': max_rejection}, 'arms': {}}
    for arm, group in arms.items():
        counters = {'runs': 0, 'accepted': 0, 'fallbacks': 0, 'cache_hits': 0, 'timeouts': 0, 'tree_changes': 0}
        rejected = {}
        for run in group:
            for key in counters:
                counters[key] += (run.get('scout') or {}).get(key, 0)
            for code, count in ((run.get('scout') or {}).get('rejected') or {}).items():
                rejected[code] = rejected.get(code, 0) + count
        reports = counters['accepted'] + sum(rejected.values())
        entry = {'runs': len(group), 'correct': sum(bool(r['correct']) for r in group),
                 'failed': sum(bool(r['failures']) for r in group),
                 'unknown_tokens': sum(r.get('host_tokens') is None for r in group),
                 'median_host_tokens': _median(r.get('host_tokens') for r in group),
                 'median_cost_usd': _median(r.get('cost_usd') for r in group),
                 'median_agent_seconds': _median(r.get('agent_seconds') for r in group),
                 'out_of_scope_runs': sum(bool(r.get('out_of_scope')) for r in group),
                 'scout': dict(counters, rejected=rejected, reports=reports,
                               rejection_rate=(sum(rejected.values()) / reports) if reports else None)}
        if arm != 'native':
            paired = []
            for scenario in sorted({r['scenario'] for r in group}):
                base = _median(native.get(scenario, []))
                treated = _median(r.get('host_tokens') for r in group if r['scenario'] == scenario)
                if base and treated is not None:
                    paired.append((scenario, base, treated))
            entry['paired'] = [{'scenario': s, 'native': b, 'scout': t, 'reduction': 1 - t / b} for s, b, t in paired]
            entry['reduction'] = (1 - sum(t for _, _, t in paired) / sum(b for _, b, _ in paired)) if paired else None
            rate = entry['scout']['rejection_rate']
            native_correct = sum(bool(r['correct']) for r in arms.get('native', [])) / max(1, len(arms.get('native', [])))
            if entry['reduction'] is None or rate is None or entry['unknown_tokens']:
                entry['verdict'] = 'insufficient evidence'
            elif (entry['reduction'] >= min_reduction and rate < max_rejection
                  and entry['correct'] / entry['runs'] >= native_correct):
                entry['verdict'] = 'passes'
            else:
                entry['verdict'] = 'fails'
        summary['arms'][arm] = entry
    passing = [(arm, e) for arm, e in summary['arms'].items() if e.get('verdict') == 'passes']
    # The default model is the fastest arm that passes; speed is the host's wall time.
    passing.sort(key=lambda item: item[1]['median_agent_seconds'] if item[1]['median_agent_seconds'] is not None else float('inf'))
    summary['fastest_passing_arm'] = passing[0][0] if passing else None
    summary['verdict'] = ('keep' if passing else 'insufficient evidence' if all(
        e.get('verdict') == 'insufficient evidence' for a, e in summary['arms'].items() if a != 'native') else 'fails the rule')
    return summary


def print_summary(summary):
    print(f"thresholds: reduction >= {summary['thresholds']['min_reduction']:.0%}, "
          f"rejection < {summary['thresholds']['max_rejection']:.0%}, correctness not below native")
    for arm, e in summary['arms'].items():
        rate = e['scout']['rejection_rate']
        print(f"{arm}: {e['correct']}/{e['runs']} correct, {e['failed']} failed, median host tokens "
              f"{e['median_host_tokens']}, median cost {e['median_cost_usd']}, median seconds {e['median_agent_seconds']}, "
              f"scout reports {e['scout']['reports']} (accepted {e['scout']['accepted']}, rejected {e['scout']['rejected'] or 0}, "
              f"rejection {'unknown' if rate is None else f'{rate:.0%}'}), fallbacks {e['scout']['fallbacks']}, "
              f"cache hits {e['scout']['cache_hits']}"
              + (f", reduction {'unknown' if e['reduction'] is None else format(e['reduction'], '.0%')}: {e['verdict']}"
                 if arm != 'native' else ''))
    print(f"verdict: {summary['verdict']}; fastest passing arm: {summary['fastest_passing_arm'] or 'none'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('scenarios', nargs='*', type=Path, help='scenario files (default: all under evals/scenarios/scout)')
    parser.add_argument('--live', action='store_true', help='explicitly authorize paid Claude and scout provider calls')
    parser.add_argument('--prepare-only', action='store_true', help='build and grade every project without any model call')
    parser.add_argument('--accept-data-sharing', action='store_true',
                        help="accept scout's disclosure for the disposable fixture projects")
    parser.add_argument('--budget-usd', type=float, help='total Claude budget, split equally across runs')
    parser.add_argument('--model', action='append', default=[], help="scout arm model; repeat for more arms ('' = provider default)")
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=900, help='seconds per Claude session')
    parser.add_argument('--scout-timeout', type=int, default=180)
    parser.add_argument('--output', type=Path, default=Path('scout-comparison.json'))
    parser.add_argument('--summarize', type=Path, help='print the decision summary of an existing report')
    args = parser.parse_args()
    if args.summarize:
        report = json.loads(args.summarize.read_text(encoding='utf-8'))
        print_summary(summarize(report))
        return 0
    if args.live == args.prepare_only:
        parser.error('choose exactly one of --live and --prepare-only')
    models = args.model or ['']
    if args.live and not (args.accept_data_sharing and args.budget_usd and args.budget_usd > 0):
        parser.error('--live needs --accept-data-sharing and a positive --budget-usd')
    if args.repeats < 1 or args.timeout < 1:
        parser.error('--repeats and --timeout must be positive')
    paths = args.scenarios or sorted(SCENARIOS.glob('*.json'))
    scenarios = [load_scenario(path) for path in paths]
    arms = [('native', None)] + [('scout:' + (m or 'default'), m) for m in models]
    total = len(scenarios) * len(arms) * args.repeats
    budget = round(args.budget_usd / total, 4) if args.live else None
    report = {'harness': 'claude', 'host_endpoint': os.environ.get('ANTHROPIC_BASE_URL') or 'anthropic',
              'host_model': os.environ.get('ANTHROPIC_MODEL') or 'harness default', 'codex': 'not run: evals/lib.py drives only the Claude CLI',
              'budget_usd': args.budget_usd, 'budget_per_run_usd': budget, 'live': args.live,
              'repeats': args.repeats, 'arms': [a for a, _ in arms],
              'scenarios': {s['id']: s['source']['rev'] for s in scenarios}, 'runs': [],
              'limits': 'Includes failed runs. Tokens are harness-reported host usage; scout provider usage is not '
                        'measured. Answers are graded by fixed checks; unnecessary edits within writable files need '
                        'human adjudication.'}
    for scenario in scenarios:
        for repeat in range(args.repeats):
            # Rotate arm order so no arm always runs first against warm provider or network state.
            shift = repeat % len(arms)
            for arm, model in arms[shift:] + arms[:shift]:
                if args.live and args.budget_usd <= sum(r.get('cost_usd') or 0 for r in report['runs']):
                    report['stopped'] = 'total budget spent'
                    break
                run = run_one(scenario, arm, model, budget, args.timeout, args.accept_data_sharing,
                              args.scout_timeout, args.live)
                run['repeat'] = repeat
                report['runs'].append(run)
                args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                status = 'ok' if run['correct'] else ('prepared' if not args.live and not run['failures'] else 'FAIL')
                print(f"{scenario['id']} {arm} #{repeat + 1}: {status}"
                      + (f" ({run['failures'][0][:200]})" if run['failures'] else ''), flush=True)
    if args.live:
        report['summary'] = summarize(report)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print_summary(report['summary'])
        return 0
    return 1 if any(r['failures'] for r in report['runs']) else 0


if __name__ == '__main__':
    sys.exit(main())
