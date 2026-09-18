"""Opt-in scout setup, configuration, and doctor reporting. Stub providers only; no network or model."""
import builtins
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_plan import clean_env
from test_scout import GIT_ENV, ROOT, SOURCE, evidence, module, report

GIT = shutil.which('git')

# The stub answers like `agy`: a version, then a model list of "id<TAB>name"
# lines after a progress line. STUB_MODE selects a failure to simulate.
STUB = r'''import os, sys
mode = os.environ.get("STUB_MODE", "ok")
args = sys.argv[1:]
if args == ["--version"]:
    if mode == "broken":
        sys.stderr.write("agy: fatal: runtime missing\n")
        sys.exit(3)
    print("1.2.6")
elif args == ["models"]:
    if mode == "nomodels":
        sys.stderr.write("not signed in\n")
        sys.exit(1)
    print("Fetching available models...")
    print("gemini-flash\tGemini Flash")
    print("gemini-pro\tGemini Pro")
else:
    sys.exit(2)
'''


class ScoutSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(os.path.realpath(self.tmp.name))
        self.root, self.bin, self.empty, self.io = base / 'repo', base / 'bin', base / 'nothing', base / 'io'
        for path in (self.root / 'src', self.bin, self.empty, self.io):
            path.mkdir(parents=True)
        (self.root / 'src/auth.py').write_text(SOURCE, encoding='utf-8')
        stub = self.bin / 'agy_stub.py'
        stub.write_text(STUB, encoding='utf-8')
        if os.name == 'nt':
            (self.bin / 'agy.cmd').write_text(f'@"{sys.executable}" "{stub}" %*\r\n', encoding='utf-8')
        else:
            launcher = self.bin / 'agy'
            launcher.write_text(f'#!{sys.executable}\n' + STUB, encoding='utf-8')
            launcher.chmod(0o755)
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True,
                              env=clean_env(**GIT_ENV), text=True).stdout

    def run_plan(self, *args, ok=None, mode='ok', path=None):
        # The PATH holds only the stub and git, so a real provider CLI on the
        # developer's machine can never answer; stdin is closed like an unattended run.
        env = clean_env(PLAN_ROOT=str(self.root), STUB_MODE=mode, PATH=self.path(path))
        result = subprocess.run([sys.executable, str(ROOT / 'bin/plan'), *args], cwd=self.root, env=env,
                                text=True, capture_output=True, stdin=subprocess.DEVNULL)
        if ok is not None:
            self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def path(self, directory=None):
        return os.pathsep.join((str(directory or self.bin), os.path.dirname(GIT)))

    @property
    def config_path(self):
        return self.root / '.coldsession-state/scout/config.json'

    def config(self):
        return json.loads(self.config_path.read_text(encoding='utf-8'))

    def setup_scout(self, *args):
        return self.run_plan('scout', 'setup', '--accept-data-sharing', *args, ok=True)

    def doctor(self):
        return json.loads(self.run_plan('doctor', '--json', ok=True).stdout)['scout']

    def test_never_set_up_means_disabled_and_nothing_written(self):
        self.assertEqual(self.doctor(), {'experimental': True, 'enabled': False})
        self.assertFalse((self.root / '.coldsession-state').exists())

    def test_setup_refuses_without_explicit_data_sharing_acceptance(self):
        refused = self.run_plan('scout', 'setup', ok=False)
        self.assertIn('--accept-data-sharing', refused.stderr)
        self.assertIn('sent to Google', refused.stdout)
        self.assertNotIn('Type yes', refused.stdout, 'closed stdin is never prompted, even NUL on Windows')
        refused = self.run_plan('scout', 'setup', '--json', ok=False)
        self.assertFalse(json.loads(refused.stdout)['enabled'])
        self.assertIn('sent to Google', refused.stderr)
        self.assertFalse(self.config_path.exists())

    def interactive(self, answer, terminal=True):
        rt = module('plan_scout_setup', ROOT / 'bin/plan')
        env = clean_env(PLAN_ROOT=str(self.root), STUB_MODE='ok', PATH=self.path())
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(rt, 'ROOT', str(self.root)), \
                mock.patch.object(rt, '_scout_terminal', lambda: terminal), \
                mock.patch.object(builtins, 'input', lambda _prompt: answer), \
                mock.patch('sys.stdout'), mock.patch('sys.stderr'):
            try:
                return rt.cmd_scout(None, ['setup'])
            except SystemExit as exc:
                return exc.code

    def test_interactive_setup_enables_only_on_yes_at_a_terminal(self):
        self.assertEqual(self.interactive('no'), 1)
        self.assertEqual(self.interactive('yes', terminal=False), 1)
        self.assertFalse(self.config_path.exists())
        self.assertEqual(self.interactive(' YES '), 0)
        self.assertTrue(self.config()['enabled'])

    def test_missing_failing_and_unknown_authentication_are_distinct(self):
        missing = self.run_plan('scout', 'setup', '--accept-data-sharing', '--json', path=self.empty, ok=False)
        self.assertEqual(json.loads(missing.stdout)['check']['result'], 'missing')
        self.assertIn('not on PATH', missing.stderr)
        broken = self.run_plan('scout', 'setup', '--accept-data-sharing', '--json', mode='broken', ok=False)
        check = json.loads(broken.stdout)['check']
        self.assertEqual(check['result'], 'failing')
        self.assertIn('exited 3', check['detail'])
        self.assertFalse(self.config_path.exists())
        self.assertEqual(self.doctor(), {'experimental': True, 'enabled': False})
        # A working CLI never proves authentication or quota.
        result = json.loads(self.run_plan('scout', 'setup', '--accept-data-sharing', '--json',
                                          mode='nomodels', ok=True).stdout)
        self.assertEqual((result['check']['result'], result['check']['auth'], result['check']['quota']),
                         ('ok', 'unknown', 'unknown'))
        self.assertIsNone(result['check']['models'])
        self.assertIn('authentication: unknown', self.setup_scout().stdout)

    def test_configuration_fields_and_defaults(self):
        self.setup_scout('--exclude', 'private/', '--timeout', '240')
        config = self.config()
        self.assertEqual({k: config[k] for k in ('enabled', 'provider', 'model', 'timeout_seconds', 'exclusions', 'threshold')},
                         {'enabled': True, 'provider': 'agy', 'model': '', 'timeout_seconds': 240,
                          'exclusions': ['private'], 'threshold': 'strict'})
        self.assertEqual(config['disclosure']['recipient'], 'Google')
        self.setup_scout()
        self.assertEqual(self.config()['timeout_seconds'], 240, 'rerunning setup keeps earlier choices')
        self.run_plan('scout', 'setup', '--accept-data-sharing', '--timeout', '5', ok=False)

    def test_model_is_validated_and_changeable_without_setup(self):
        self.run_plan('scout', 'model', 'gemini-pro', ok=False)  # not set up yet
        refused = self.run_plan('scout', 'setup', '--accept-data-sharing', '--model', 'gemini-ultra', ok=False)
        self.assertIn('gemini-flash', refused.stderr)
        self.assertFalse(self.config_path.exists())
        self.setup_scout('--model', 'gemini-flash')
        self.assertEqual(self.config()['model'], 'gemini-flash')
        disclosed = self.config()['disclosure']
        self.run_plan('scout', 'model', 'gemini-ultra', ok=False)
        self.run_plan('scout', 'model', 'gemini-pro', ok=True)
        self.assertEqual((self.config()['model'], self.config()['disclosure']), ('gemini-pro', disclosed))
        self.run_plan('scout', 'model', '--default', ok=True)
        self.assertEqual(self.config()['model'], '')
        self.assertEqual(self.doctor()['model'], 'provider default')
        # Without a model list the name cannot be checked; it is kept and flagged.
        unchecked = self.run_plan('scout', 'model', 'anything', mode='nomodels', ok=True)
        self.assertIn('not validated', unchecked.stdout)

    def test_always_excluded_paths_cannot_be_removed(self):
        self.setup_scout('--exclude', 'private')
        for entry in ('.env', 'keys/server.pem', '.git/config', '.coldsession-state', '.coldsession-state/scout'):
            refused = self.run_plan('scout', 'exclude', 'remove', entry, ok=False)
            self.assertIn('always excluded', refused.stderr)
        self.run_plan('scout', 'exclude', 'add', 'notes', ok=True)
        self.run_plan('scout', 'exclude', 'add', '.', ok=False)
        self.run_plan('scout', 'exclude', 'remove', 'private', ok=True)
        self.assertEqual(self.config()['exclusions'], ['notes'])
        self.run_plan('scout', 'exclude', 'remove', 'private', ok=False)
        shown = json.loads(self.run_plan('scout', 'exclude', 'add', 'notes', '--json', ok=True).stdout)
        self.assertEqual(shown['always_excluded'], ['sensitive()', '.coldsession-state'])

    def test_disable_keeps_reports_and_stats(self):
        self.assertIn('not set up', self.run_plan('scout', 'disable', ok=True).stdout)
        self.setup_scout()
        cached = self.root / '.coldsession-state/scout/reports/kept.json'
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text('{}', encoding='utf-8')
        self.run_plan('scout', 'disable', ok=True)
        self.assertFalse(self.config()['enabled'])
        self.assertTrue(cached.exists())
        self.assertTrue((self.root / '.coldsession-state/scout/stats.json').exists())
        self.assertFalse(self.doctor()['enabled'])

    def test_configuration_and_stats_are_never_committed(self):
        self.setup_scout('--exclude', 'private')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all').strip(), '')

    def test_doctor_reports_fields_and_counters_concisely(self):
        self.setup_scout('--model', 'gemini-flash')
        # Request and reports live outside the repository so the tree stays clean
        # and the accepted report is cached.
        request_path = self.io / 'request.json'
        request = self.run_plan('scout', 'request', 'locate', 'symbol=refresh_token', '--purpose', 'find it',
                                '--include', 'src', ok=True).stdout
        request_path.write_text(request, encoding='utf-8')
        good = self.io / 'good.json'
        good.write_text(json.dumps(report(answer='Defined in auth [E1].', items=[
            evidence('E1', 'src/auth.py', 1, ['def refresh_token(session):'])])), encoding='utf-8')
        bad = self.io / 'bad.json'
        bad.write_text(json.dumps(report(answer='Defined somewhere.', items=[
            evidence('E1', 'src/missing.py', 1, ['x'])])), encoding='utf-8')
        self.run_plan('scout', 'validate', str(good), '--request', str(request_path), ok=True)
        self.run_plan('scout', 'validate', str(bad), '--request', str(request_path), ok=False)
        self.run_plan('scout', 'cached', '--request', str(request_path), ok=True)
        scout = self.doctor()
        self.assertEqual({k: scout[k] for k in ('experimental', 'enabled', 'provider', 'model', 'cli_detected')},
                         {'experimental': True, 'enabled': True, 'provider': 'agy', 'model': 'gemini-flash',
                          'cli_detected': True})
        self.assertEqual(scout['last_check']['result'], 'ok')
        self.assertTrue(scout['last_check']['at'])
        counters = scout['counters']
        self.assertEqual({k: counters[k] for k in ('runs', 'accepted', 'fallbacks', 'cache_hits')},
                         {'runs': 0, 'accepted': 1, 'fallbacks': 0, 'cache_hits': 1})
        self.assertGreaterEqual(sum(counters['rejected'].values()), 1)
        human = self.run_plan('doctor', ok=True).stdout
        self.assertEqual(len([line for line in human.splitlines() if line.startswith('scout:')]), 1)

    def test_invalid_config_is_reported_not_trusted(self):
        self.config_path.parent.mkdir(parents=True)
        self.config_path.write_text(json.dumps({'enabled': 'yes', 'provider': 'agy'}), encoding='utf-8')
        scout = self.doctor()
        self.assertFalse(scout['enabled'])
        self.assertIn('invalid scout config', scout['error'])
        self.run_plan('scout', 'model', 'gemini-pro', ok=False)
        # Setup repairs it and keeps exclusions written before setup existed.
        self.config_path.write_text(json.dumps({'exclusions': ['private']}), encoding='utf-8')
        self.setup_scout()
        self.assertEqual((self.config()['enabled'], self.config()['exclusions']), (True, ['private']))


if __name__ == '__main__':
    unittest.main()
