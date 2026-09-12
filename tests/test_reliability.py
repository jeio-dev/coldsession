"""Deterministic format-2 and upgrade regression tests; no model calls."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_plan import phase_text, clean_env

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    result = importlib.util.module_from_spec(spec)
    loader.exec_module(result)
    return result


class ReliabilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.test_path = os.environ.get('PATH', '')
        if os.name != 'nt':
            tool_dir = self.root / 'test-bin'
            tool_dir.mkdir()
            (tool_dir / 'python').symlink_to(sys.executable)
            self.test_path = str(tool_dir) + os.pathsep + self.test_path
        self.phase = self.root / 'docs/plans/01-test.md'
        self.phase.parent.mkdir(parents=True)
        (self.root / 'PLAN.md').write_text('---\ncurrent: docs/plans/01-test.md\n---\n- [ ] docs/plans/01-test.md\n', encoding='utf-8')
        (self.root / 'src').mkdir()
        (self.root / 'src/a.py').write_text('a = 1\n', encoding='utf-8')
        (self.root / 'src/b.py').write_text('b = 1\n', encoding='utf-8')
        self.rt = module('runtime_test', ROOT / 'bin/plan')
        self.rt.ROOT = str(self.root)
        self.rt.INDEX = str(self.root / 'PLAN.md')
        self.rt.AGENTS_PATH = str(self.root / 'AGENTS.md')
        self.write()

    def write(self, **kwargs):
        self.phase.write_text(phase_text(workflow='2.0.0', **kwargs) + '\n## Constraints\n\nPreserve data integrity.\n', encoding='utf-8')

    def p(self):
        return self.rt.read_phase(str(self.phase))

    def run_plan(self, *args, ok=True, env=None, payload=None):
        extra = {'PLAN_ROOT': str(self.root), 'PATH': self.test_path, 'CODEX_THREAD_ID': 'test-coordinator'}
        extra.update(env or {})
        result = subprocess.run([sys.executable, str(ROOT / 'bin/plan'), *args],
                                env=clean_env(**extra),
                                input=json.dumps(payload) if payload else '',
                                text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def approve(self):
        self.run_plan('begin', 'review')
        self.run_plan('finish', 'review')
        self.run_plan('begin', 'approve')
        self.run_plan('finish', 'approve', '--pass')
        self.phase.write_text(self.phase.read_text(encoding='utf-8').replace('status: draft', 'status: approved', 1), encoding='utf-8')

    def edit(self, old, new):
        self.phase.write_text(self.phase.read_text(encoding='utf-8').replace(old, new), encoding='utf-8')

    def test_readiness_requires_spec_not_just_revision(self):
        self.approve()
        self.edit('Acceptance Criteria: observable', 'Acceptance Criteria: different')
        self.run_plan('start', 'T1', ok=False)
        self.assertIn('replan', self.run_plan('recommend').stdout)

    def test_missing_readiness_refuses_execution(self):
        self.write(status='approved', reviewed=1)
        self.run_plan('start', 'T1', ok=False)

    def test_operational_status_owner_and_findings_do_not_change_spec(self):
        original = self.rt.specification(self.p())
        self.edit('status: pending', 'status: done')
        self.edit('files: [src/a.py]}', 'files: [src/a.py], owner: worker}')
        self.edit('## Findings', '## Findings\n\nF1 | Low | Review | T1 | open | Concrete defect | fix')
        self.assertEqual(original, self.rt.specification(self.p()))

    def test_dependencies_reads_constraints_and_headings_change_spec(self):
        for old, new in [('deps: []', 'deps: [T1]'), ('files: [src/a.py]', 'files: [src/a.py], reads: [src/b.py]'),
                         ('Preserve data integrity.', 'Preserve accessibility.'), ('## T1', '## T1 changed')]:
            self.write()
            old_spec = self.rt.specification(self.p())
            self.edit(old, new)
            self.assertNotEqual(old_spec, self.rt.specification(self.p()))

    def test_review_cannot_certify_concurrent_spec_edit(self):
        self.run_plan('begin', 'review')
        self.edit('Goal: test', 'Goal: changed')
        self.run_plan('finish', 'review', ok=False)

    def test_completion_requires_current_successful_evidence(self):
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('done', 'T1', ok=False)
        self.run_plan('verify', 'T1')
        (self.root / 'src/a.py').write_text('changed', encoding='utf-8')
        self.run_plan('done', 'T1', ok=False)
        self.run_plan('verify', 'T1')
        self.run_plan('done', 'T1')

    def test_failed_verify_cannot_complete(self):
        self.edit('`python -V`', '`python -c "raise SystemExit(3)"`')
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('verify', 'T1', ok=False)
        self.run_plan('done', 'T1', ok=False)

    def test_interrupted_verification_invalidates_previous_success(self):
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('verify', 'T1')
        with mock.patch.object(self.rt, 'bounded_run', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.rt.cmd_verify(self.p(), ['T1'])
        self.assertFalse(self.rt.evidence_valid(self.p(), 'T1'))
        self.run_plan('done', 'T1', ok=False)

    def test_manual_and_visual_are_explicit_attestations(self):
        self.edit('Verify: `python -V` exits 0', 'Verify: visual: tab order reaches save\nVerify: manual: review exported file')
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('verify', 'T1', ok=False)
        self.run_plan('verify', 'T1', '--attest', 'Observed tab order and checked export')
        record = json.loads(self.phase.with_suffix('.evidence.json').read_text())['T1']
        self.assertEqual([c['kind'] for c in record['checks']], ['visual', 'manual'])
        self.assertIn('attestation', record['results'][0])

    def test_duplicate_ids_rejected_before_mutation(self):
        self.edit('tasks:', 'tasks:\n  T1: {deps: [], status: pending, files: [src/other.py]}')
        self.run_plan('lint', ok=False)
        self.run_plan('begin', 'review', ok=False)

    def test_invalid_current_paths_rejected(self):
        for path in ('../outside.md', 'src/a.py', 'docs/plans/01-test.log.md', 'C:/outside.md'):
            (self.root / 'PLAN.md').write_text('---\ncurrent: ' + path + '\n---', encoding='utf-8')
            self.run_plan('status', ok=False)

    def test_replan_preserves_completed_work_and_requires_explicit_claim_recovery(self):
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('verify', 'T1')
        self.run_plan('done', 'T1')
        self.run_plan('start', 'T2')
        self.run_plan('replan', ok=False)
        self.run_plan('replan', '--recover-claims')
        self.assertEqual(self.p()['tasks']['T1']['status'], 'done')
        self.assertEqual(self.p()['tasks']['T2']['status'], 'pending')
        self.assertEqual(self.p()['meta']['status'], 'draft')

    def test_unavailable_lock_fails_closed(self):
        lock_dir = self.root / 'not-a-directory'
        lock_dir.write_text('occupied')
        before = self.phase.read_bytes()
        self.run_plan('begin', 'review', env={'PLAN_LOCK_DIR': str(lock_dir)}, ok=False)
        self.assertEqual(before, self.phase.read_bytes())

    def test_interrupted_atomic_write_preserves_original(self):
        before = self.phase.read_bytes()
        with mock.patch.object(self.rt.os, 'replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.rt.atomic_write(str(self.phase), 'replacement')
        self.assertEqual(before, self.phase.read_bytes())

    def test_interrupted_close_transaction_can_replay_twice(self):
        other = str(self.root / 'PLAN.md')
        original = self.rt.atomic_write
        def fail_second(path, text):
            if os.path.normcase(path) == os.path.normcase(str(self.phase)):
                raise OSError('power loss')
            original(path, text)
        with mock.patch.object(self.rt, 'atomic_write', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.rt.transaction({other: 'index closed', str(self.phase): 'phase closed'})
        self.rt.recover_transaction()
        self.rt.recover_transaction()
        self.assertEqual(self.phase.read_text(), 'phase closed')
        self.assertEqual(Path(other).read_text(), 'index closed')

    def test_brief_does_not_include_every_dependency_file(self):
        self.write(tasks={'T1': ([], 'done', ['src/a.py']), 'T2': (['T1'], 'pending', ['src/b.py'])})
        reads = self.rt.read_set(self.p(), 'T2')
        self.assertNotIn('src/a.py', reads)
        self.edit('files: [src/b.py]}', 'files: [src/b.py], reads: [src/a.py]}')
        self.assertIn('src/a.py', self.rt.read_set(self.p(), 'T2'))

    def test_handoffs_select_relevant_non_superseded_entries(self):
        path = self.phase.with_suffix('.handoffs.json')
        path.write_text(json.dumps([{'id': 'a', 'task': 'T1'},
                                    {'id': 'b', 'task': 'T1', 'supersedes': ['a']},
                                    {'id': 'c', 'task': 'T2'}]))
        self.assertEqual([r['id'] for r in self.rt.relevant_handoffs(self.p(), 'T1')], ['b'])

    def test_handoff_can_be_recorded_without_out_of_scope_scratch_file(self):
        self.approve()
        self.run_plan('start', 'T1')
        entry = {'decisions': 'Reused existing behavior', 'evidence': 'verification pending',
                 'limitations': 'none', 'affects': ['T2'], 'provenance': 'T1 implementation', 'supersedes': []}
        self.run_plan('handoff', 'T1', json.dumps(entry))
        self.assertTrue(self.phase.with_suffix('.handoffs.json').exists())

    def test_read_authorization_is_not_write_authorization(self):
        self.edit('files: [src/a.py]}', 'files: [src/a.py], reads: [src/b.py]}')
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('guard', 'read', 'src/b.py')
        self.run_plan('guard', 'write', 'src/b.py', ok=False)

    def test_patch_shell_and_sensitive_payloads(self):
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('guard', 'write', payload={'name': 'apply_patch', 'input': '*** Begin Patch\n*** Update File: src/b.py\n+x\n*** End Patch'}, ok=False)
        self.run_plan('guard', 'write', payload={'tool_name': 'exec_command', 'arguments': {'cmd': 'python arbitrary.py'}}, ok=False)
        self.run_plan('guard', 'read', '.env', ok=False)

    def test_link_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            link = self.root / 'src/link'
            try:
                link.symlink_to(external, target_is_directory=True)
            except OSError:
                if os.name == 'nt':
                    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), external], capture_output=True)
                    if result.returncode:
                        self.skipTest('neither symlinks nor junctions available')
                else:
                    raise
            with self.assertRaises(ValueError):
                self.rt.scope_path('src/link/secret.py')
            # Remove only this verified junction/link, never its target.
            link.unlink() if link.is_symlink() else link.rmdir()

    def test_output_bounded_and_credentials_filtered(self):
        result = self.rt.bounded_run([sys.executable, '-c', 'print("token=secret-value"); print("x"*20000)'], shell=False)
        self.assertTrue(result['truncated'])
        self.assertNotIn('secret-value', result['output'])
        self.assertEqual(result['exit'], 0)

    def test_doctor_json_reports_unknown_trust(self):
        report = json.loads(self.run_plan('doctor', '--json').stdout)
        self.assertIn('unknown', report['trust'])
        self.assertTrue(report['gaps'])

    def test_assignments_default_two_and_reject_stale_results(self):
        self.approve()
        assignments = json.loads(self.run_plan('assign', 'codex').stdout)
        self.assertEqual(len(assignments), 2)
        result = {**assignments['T1'], 'assignment': 'superseded', 'outcome': 'success'}
        (self.root / 'result.json').write_text(json.dumps(result))
        self.run_plan('integrate', 'result.json', ok=False)
        self.run_plan('assign', 'codex', ok=False)

    def test_workers_cannot_mutate_shared_state(self):
        self.approve()
        self.run_plan('assign', 'codex', env={'CS_WORKER_ASSIGNMENT': 'worker'}, ok=False)

    def test_native_worker_binding_grants_only_its_source_scope(self):
        self.approve()
        self.run_plan('assign', 'codex')
        self.run_plan('assign', '--bind', 'T1', 'native-worker')
        worker_env = {'CODEX_THREAD_ID': 'native-worker'}
        self.run_plan('guard', 'write', 'src/a.py', env=worker_env)
        self.run_plan('guard', 'write', 'src/b.py', env=worker_env, ok=False)
        self.run_plan('verify', 'T1', env=worker_env, ok=False)
        self.run_plan('assign', '--bind', 'T1', 'replacement-worker', ok=False)

    def test_anonymous_single_build_uses_its_only_scope(self):
        self.approve()
        anonymous = {'CODEX_THREAD_ID': ''}
        self.run_plan('start', 'T1', env=anonymous)
        self.run_plan('guard', 'read', env=anonymous, payload={
            'session_id': 'hook-only-session', 'tool_input': {'file_path': 'src/a.py'}})

    def test_team_without_stable_identity_is_unavailable(self):
        self.approve()
        self.run_plan('assign', 'codex', env={'CODEX_THREAD_ID': ''}, ok=False)

    def test_running_normalized_file_overlap_is_rejected(self):
        self.edit('src/b.py', 'src/a.py')
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('start', 'T2', ok=False)

    def test_parallel_writers_cannot_race_supporting_reads(self):
        self.edit('files: [src/b.py]}', 'files: [src/b.py], reads: [src/a.py]}')
        self.approve()
        assignments = json.loads(self.run_plan('assign', 'codex').stdout)
        self.assertEqual(list(assignments), ['T1'])

    def test_complete_approved_verified_phase_closes(self):
        self.approve()
        for tid in ('T1', 'T2'):
            self.run_plan('start', tid)
            self.run_plan('verify', tid)
            self.run_plan('done', tid)
        self.run_plan('begin', 'close')
        self.run_plan('finish', 'close', '--pass')
        self.assertEqual(self.p()['meta']['status'], 'closed')
        self.assertIn('[x]', (self.root / 'PLAN.md').read_text())
        self.run_plan('replan', ok=False)

    def test_coordinator_integrates_matching_verified_results(self):
        self.approve()
        assignments = json.loads(self.run_plan('assign', 'codex').stdout)
        self.run_plan('verify', 'T1')
        self.run_plan('done', 'T1', ok=False)
        (self.root / 'result.json').write_text(json.dumps({**assignments['T1'], 'outcome': 'success'}))
        self.run_plan('integrate', 'result.json')
        self.assertEqual(self.p()['tasks']['T1']['status'], 'done')

    def test_blocker_stops_integration_until_replan(self):
        self.approve()
        self.run_plan('assign', 'claude')
        self.run_plan('block', 'T1', 'required behavior violates the approved contract')
        self.assertEqual(self.p()['meta']['status'], 'draft')
        self.assertTrue(self.p()['findings'])
        self.run_plan('verify', 'T2', ok=False)

    def test_automated_commands_cannot_be_overridden_by_attestation(self):
        self.edit('`python -V`', '`python -c "raise SystemExit(1)"`')
        self.approve()
        self.run_plan('start', 'T1')
        self.run_plan('verify', 'T1', '--attest', 'claims success', ok=False)
        self.run_plan('done', 'T1', ok=False)

    def test_upgrade_journal_blocks_mutations(self):
        self.rt.save_json(self.rt.state_path('upgrade.json'), {'status': 'applying'})
        self.run_plan('begin', 'review', ok=False)


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inst = module('installer_test', ROOT / 'bin/cs_install.py')

    def run_install(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / 'bin/cs_install.py'), str(self.root), *args],
                                env=clean_env(), text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def install(self):
        preview = json.loads(self.run_install('--preview').stdout)
        self.run_install('--apply', preview['preview'])
        return preview

    def test_preview_changes_nothing_then_apply_is_idempotent(self):
        preview = json.loads(self.run_install().stdout)
        self.assertFalse((self.root / '.claude/bin/plan').exists())
        self.run_install('--apply', preview['preview'])
        self.run_install('--apply', preview['preview'])
        self.assertTrue((self.root / '.claude/bin/plan').exists())

    def test_modified_preflight_inputs_refuse_apply(self):
        preview = json.loads(self.run_install().stdout)
        (self.root / 'PLAN.md').write_text('intervening work')
        self.run_install('--apply', preview['preview'], ok=False)
        self.assertFalse((self.root / '.claude/bin/plan').exists())

    def test_custom_runtime_conflict_is_never_overwritten(self):
        self.install()
        path = self.root / '.claude/bin/plan'
        path.write_text('custom runtime')
        preview = json.loads(self.run_install().stdout)
        self.assertIn('.claude/bin/plan', preview['conflicts'])
        self.run_install('--apply', preview['preview'], ok=False)
        self.assertEqual(path.read_text(), 'custom runtime')

    def test_unrelated_config_and_custom_commands_preserved(self):
        self.install()
        path = self.root / '.claude/settings.json'
        settings = json.loads(path.read_text())
        settings['model'] = 'user-selected'
        settings['permissions'] = {'deny': ['Bash(rm *)']}
        path.write_text(json.dumps(settings))
        custom = self.root / '.claude/commands/cs-build.md'
        custom.write_text('local build instructions')
        preview = self.install()
        self.assertIn('.claude/commands/cs-build.md', preview['preserved_customizations'])
        self.assertEqual(custom.read_text(), 'local build instructions')
        self.assertEqual(json.loads(path.read_text())['permissions'], settings['permissions'])

    def test_legacy_migration_preserves_history_without_inventing_scope_or_evidence(self):
        path = self.root / 'docs/plans/01-test.md'
        path.parent.mkdir(parents=True)
        path.write_text(phase_text(status='approved', reviewed=1, ready=1,
                                   tasks={'T1': ([], 'done', ['src/a.py'])}), encoding='utf-8')
        preview = self.install()
        self.assertTrue(preview['migrations'])
        text = path.read_text()
        self.assertIn('status: done, files: [], reads: [src/a.py]', text)
        self.assertIn('status: draft', text)
        self.assertIn('Migration', text)
        self.assertFalse(path.with_suffix('.evidence.json').exists())

    def test_closed_history_is_not_rewritten(self):
        path = self.root / 'docs/plans/01-test.md'
        path.parent.mkdir(parents=True)
        original = phase_text(status='closed').encode()
        path.write_bytes(original)
        self.install()
        self.assertEqual(path.read_bytes(), original)

    def test_semantically_unchanged_approved_format_two_is_preserved(self):
        path = self.root / 'docs/plans/01-test.md'
        path.parent.mkdir(parents=True)
        rt = self.inst.runtime()
        original = phase_text(workflow='2.0.0', status='approved', ready=1, reviewed=1) + '\n## Constraints\n\nNone.\n'
        path.write_text(original, encoding='utf-8')
        fingerprint = rt.specification(rt.read_phase(str(path)))
        path.write_text(rt.set_metas(original, {'ready-spec': fingerprint, 'reviewed-spec': fingerprint}), encoding='utf-8')
        before = path.read_bytes()
        self.install()
        self.assertEqual(path.read_bytes(), before)

    def test_application_failure_restores_files_and_can_be_retried(self):
        preview = json.loads(self.run_install().stdout)
        rt = self.inst.runtime()
        rt.ROOT, rt.INDEX = str(self.root), str(self.root / 'PLAN.md')
        args = type('Args', (), {'apply': preview['preview']})()
        original = self.inst.atomic_bytes
        triggered = []
        def fail_install(path, data):
            if path == self.root / '.claude/bin/plan' and not triggered:
                triggered.append(True)
                raise OSError('simulated interrupted replacement')
            original(path, data)
        with mock.patch.object(self.inst, 'atomic_bytes', side_effect=fail_install):
            with self.assertRaises(OSError):
                self.inst.apply(args, self.root, rt)
        self.assertFalse((self.root / '.claude/bin/plan').exists())
        journal = json.loads((self.root / '.coldsession-state/upgrade.json').read_text())
        self.assertEqual(journal['status'], 'rolled-back')
        self.run_install('--apply', preview['preview'])

    def test_active_claim_refuses_preview_even_if_old(self):
        path = self.root / 'docs/plans/01-test.md'
        path.parent.mkdir(parents=True)
        path.write_text(phase_text(status='approved', tasks={'T1': ([], 'in_progress', ['a.py'])}), encoding='utf-8')
        self.run_install(ok=False)

    def test_interrupted_application_rolls_back_and_recovery_repeats(self):
        path = self.root / 'original.txt'
        path.write_bytes(b'original')
        backup = self.root / '.coldsession-state/backups/test/original.txt'
        backup.parent.mkdir(parents=True)
        backup.write_bytes(b'original')
        journal = {'status': 'applying', 'backup': '.coldsession-state/backups/test',
                   'originals': {'original.txt': {'sha': self.inst.sha(b'original'), 'mode': path.stat().st_mode}},
                   'after': {'original.txt': self.inst.sha(b'replacement')}}
        path.write_bytes(b'replacement')
        self.inst.rollback(self.root, journal)
        self.inst.rollback(self.root, journal)
        self.assertEqual(path.read_bytes(), b'original')
        self.assertTrue(backup.exists())

    def test_rollback_refuses_overwriting_intervening_changes(self):
        path = self.root / 'a.txt'
        path.write_bytes(b'new user work')
        journal = {'backup': 'backups', 'originals': {'a.txt': {'sha': 'original'}}, 'after': {'a.txt': 'installed'}}
        with self.assertRaises(ValueError):
            self.inst.rollback(self.root, journal)
        self.assertEqual(path.read_bytes(), b'new user work')
