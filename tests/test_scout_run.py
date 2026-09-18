"""Scout provider runs through a stub `agy` on PATH. No network, model, or real provider CLI."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

from test_plan import clean_env
from test_scout import GIT_ENV, ROOT, SOURCE, evidence, report

GIT = shutil.which('git')

# The stub answers setup's checks like agy, then plays one scripted response
# per print-mode call from STUB_PLAN and logs each call's arguments, working
# directory, and the files it could see there.
STUB = r'''import json, os, subprocess, sys, time
args = sys.argv[1:]
if args == ["--version"]:
    print("1.2.6")
    sys.exit(0)
if args == ["models"]:
    print("gemini-flash\tGemini Flash")
    sys.exit(0)
plan = json.load(open(os.environ["STUB_PLAN"], encoding="utf-8"))
log = plan["log"]
calls = open(log, encoding="utf-8").read().splitlines() if os.path.exists(log) else []
seen = sorted(os.path.relpath(os.path.join(b, f), os.getcwd()).replace(os.sep, "/")
              for b, _d, fs in os.walk(os.getcwd()) for f in fs)
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"args": args, "cwd": os.getcwd(), "seen": seen}) + "\n")
step = plan["responses"][min(len(calls), len(plan["responses"]) - 1)]
kind = step["kind"]
if kind == "sleep":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    open(plan["pidfile"], "w").write(str(child.pid))
    time.sleep(120)
if kind == "write_repo":
    open(step["path"], "w").write("provider was here\n")
if kind == "write_stage":
    open("notes.txt", "w").write("scratch\n")
if kind == "garbage":
    print("I could not produce JSON, sorry.")
    sys.exit(0)
body = json.dumps(step["report"]).replace("{CWD}", os.getcwd().replace("\\", "/"))
sys.stderr.write("progress on stderr\n")
print(json.dumps({"status": "SUCCESS", "response": "done", "structured_output": json.loads(body),
                  "usage": {"total_tokens": 10}}))
'''


def install_stub(directory, name='agy'):
    """A launcher the OS runs directly, so multi-line arguments arrive intact.

    Windows batch files cannot carry a newline in an argument, so there the stub
    is wrapped in the distlib console launcher that pip uses for scripts.
    """
    if os.name != 'nt':
        path = directory / name
        path.write_text(f'#!{sys.executable}\n' + STUB, encoding='utf-8')
        path.chmod(0o755)
        return path
    try:
        from pip._vendor import distlib
    except ImportError:
        raise unittest.SkipTest('pip is needed to build a Windows console launcher for the stub')
    launcher = Path(distlib.__file__).parent / ('t64.exe' if sys.maxsize > 2 ** 32 else 't32.exe')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('__main__.py', STUB)
    path = directory / (name + '.exe')
    path.write_bytes(launcher.read_bytes() + b'#!"' + sys.executable.encode() + b'"\n' + archive.getvalue())
    return path


def alive(pid):
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x00100000 | 0x1000, False, pid)
        if not handle:
            return False
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) != 0
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # a zombie still answers kill(0); ask ps for its state
        state = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout
    except OSError:
        return True
    return bool(state.strip()) and not state.strip().startswith('Z')


def good_report():
    return report(answer='Defined in auth [E1].', items=[
        evidence('E1', 'src/auth.py', 1, ['def refresh_token(session):', '    """Renew the session token."""'])])


def shape_error():
    return dict(good_report(), status='maybe')


class ScoutRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(os.path.realpath(self.tmp.name))
        self.root, self.bin, self.empty, self.io = base / 'repo', base / 'bin', base / 'nothing', base / 'io'
        for path in (self.root / 'src', self.root / 'private', self.bin, self.empty, self.io):
            path.mkdir(parents=True)
        (self.root / 'src/auth.py').write_text(SOURCE, encoding='utf-8')
        (self.root / 'src/.env').write_text('TOKEN=refresh_token\n', encoding='utf-8')
        (self.root / 'private/plans.md').write_text('refresh_token roadmap\n', encoding='utf-8')
        (self.root / 'README.md').write_text('outside the include\n', encoding='utf-8')
        install_stub(self.bin)
        self.log = self.io / 'calls.log'
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'fixture')
        self.run_plan('scout', 'setup', '--accept-data-sharing', '--exclude', 'private', ok=True)
        self.request = self.io / 'request.json'
        self.request.write_text(self.run_plan('scout', 'request', 'locate', 'symbol=refresh_token',
                                              '--purpose', 'find it', '--include', 'src', '--include', 'private',
                                              ok=True).stdout, encoding='utf-8')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True,
                              env=clean_env(**GIT_ENV), text=True).stdout

    def run_plan(self, *args, ok=None, path=None, responses=None):
        # PATH holds only the stub and git, so a real provider CLI can never answer.
        plan = self.io / 'plan.json'
        plan.write_text(json.dumps({'log': str(self.log), 'pidfile': str(self.io / 'child.pid'),
                                    'responses': responses or [{'kind': 'report', 'report': good_report()}]}),
                        encoding='utf-8')
        env = clean_env(PLAN_ROOT=str(self.root), STUB_PLAN=str(plan),
                        PATH=os.pathsep.join((str(path or self.bin), os.path.dirname(GIT))))
        result = subprocess.run([sys.executable, str(ROOT / 'bin/plan'), *args], cwd=self.root, env=env,
                                text=True, capture_output=True, stdin=subprocess.DEVNULL)
        if ok is not None:
            self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def scout(self, *responses, ok=None, path=None, as_json=False):
        args = ['scout', 'run', '--request', str(self.request)] + (['--json'] if as_json else [])
        return self.run_plan(*args, ok=ok, path=path, responses=list(responses) or None)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]

    def counters(self):
        return json.loads(self.run_plan('doctor', '--json', ok=True).stdout)['scout']['counters']

    def assert_fallback(self, result, *words):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout)
        self.assertRegex(lines[0], r'^scout unavailable \(.+\); explore natively$')
        for word in words:
            self.assertIn(word, lines[0])

    def set_config(self, **change):
        path = self.root / '.coldsession-state/scout/config.json'
        config = json.loads(path.read_text(encoding='utf-8'))
        config.update(change)
        path.write_text(json.dumps(config), encoding='utf-8')

    def test_success_runs_read_only_in_a_scoped_copy(self):
        result = self.scout({'kind': 'report', 'report': good_report()}, ok=True)
        self.assertIn('scout locate: answered (orientation only', result.stdout)
        self.assertIn('E1 src/auth.py:1-2', result.stdout)
        self.assertIn('verified: snippets 1', result.stdout)
        self.assertIn('agy (provider default), attempts 1', result.stdout)
        self.assertIn('cache stored', result.stdout)
        [call] = self.calls()
        args = call['args']
        for flag in ('--dangerously-skip-permissions', '--mode', '--sandbox'):
            self.assertNotIn(flag, args)
        request = json.loads(self.request.read_text(encoding='utf-8'))
        self.assertTrue(args[-1].startswith('--print=' + request['prompt'].rstrip('\n') + '\n\n'),
                        'the multi-line template arrives intact')
        self.assertIn("Shell and terminal commands are unavailable", args[-1])
        self.assertEqual(args[args.index('--output-format') + 1], 'json')
        schema = json.loads(args[args.index('--json-schema') + 1])
        self.assertEqual(schema['$id'], 'coldsession-scout/1/report')
        self.assertNotIn('steps', schema['properties'], 'a locate report has no steps')
        workspace = args[args.index('--add-dir') + 1]
        self.assertEqual(os.path.realpath(workspace), os.path.realpath(call['cwd']))
        self.assertNotEqual(os.path.realpath(workspace), str(self.root))
        # Only in-scope, non-excluded, non-sensitive files reach the provider.
        self.assertEqual(call['seen'], ['src/auth.py'])
        self.assertFalse(os.path.exists(workspace), 'the scratch copy is removed')
        counters = self.counters()
        self.assertEqual({k: counters[k] for k in ('runs', 'accepted', 'fallbacks', 'retries')},
                         {'runs': 1, 'accepted': 1, 'fallbacks': 0, 'retries': 0})
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all').strip(), '')

    def test_paths_inside_the_scratch_copy_are_mapped_back(self):
        cited = good_report()
        cited['evidence'][0]['file'] = '{CWD}/src/auth.py'
        result = json.loads(self.scout({'kind': 'report', 'report': cited}, ok=True, as_json=True).stdout)
        self.assertEqual(result['report']['evidence'][0]['file'], 'src/auth.py')
        self.assertEqual(result['report']['meta'], {'provider': 'agy', 'model': 'provider default'})

    def test_code_that_looks_like_a_credential_is_parsed_intact(self):
        # Output is parsed raw; credential filtering applies only to what is shown or kept.
        quoted = report(answer='It issues a token [E1].', items=[
            evidence('E1', 'src/auth.py', 3, ['    token = session.issue()', '    session.store(token)'])])
        result = self.scout({'kind': 'report', 'report': quoted}, ok=True)
        self.assertIn('E1 src/auth.py:3-4', result.stdout)

    def test_invalid_shape_is_retried_once(self):
        result = self.scout({'kind': 'report', 'report': shape_error()},
                            {'kind': 'report', 'report': good_report()}, ok=True)
        self.assertIn('attempts 2', result.stdout)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(self.counters()['retries'], 1)

    def test_invalid_shape_twice_falls_back(self):
        result = self.scout({'kind': 'garbage'}, {'kind': 'report', 'report': shape_error()})
        self.assert_fallback(result, 'invalid report shape twice')
        self.assertEqual(len(self.calls()), 2)
        counters = self.counters()
        self.assertEqual((counters['fallbacks'], counters['accepted']), (1, 0))
        self.assertEqual(counters['rejected'].get('invalid_shape'), 1)

    def test_failed_validation_is_not_retried(self):
        wrong = good_report()
        wrong['evidence'][0]['snippet'] = 'def something_else():\n    pass'
        result = self.scout({'kind': 'report', 'report': wrong}, {'kind': 'report', 'report': good_report()})
        self.assert_fallback(result, 'failed validation', 'snippet_mismatch')
        self.assertEqual(len(self.calls()), 1)
        detail = json.loads(self.scout({'kind': 'report', 'report': wrong}, as_json=True).stdout)
        self.assertFalse(detail['accepted'])
        self.assertEqual(detail['reasons'][0]['code'], 'snippet_mismatch')

    def test_timeout_kills_the_whole_process_tree(self):
        self.set_config(timeout_seconds=10)
        started = time.monotonic()
        result = self.scout({'kind': 'sleep'})
        self.assert_fallback(result, 'timed out after 10s')
        self.assertLess(time.monotonic() - started, 60)
        pid = int((self.io / 'child.pid').read_text())
        deadline = time.monotonic() + 10
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(alive(pid), 'the provider child process outlived the timeout')
        self.assertEqual(self.counters()['timeouts'], 1)

    def test_working_tree_change_is_rejected_alerted_and_not_reverted(self):
        target = self.root / 'src/injected.py'
        result = self.scout({'kind': 'write_repo', 'path': str(target), 'report': good_report()})
        self.assert_fallback(result, 'changed the working tree', 'nothing was reverted')
        self.assertIn('SCOUT ALERT', result.stderr)
        self.assertIn('src/injected.py', result.stderr)
        self.assertEqual(target.read_text(), 'provider was here\n', 'the change is left for the user')
        self.assertEqual(len(self.calls()), 1)
        counters = self.counters()
        self.assertEqual((counters['tree_changes'], counters['accepted']), (1, 0))
        self.assertFalse((self.root / '.coldsession-state/scout/reports').exists())

    def test_modified_tracked_file_change_is_detected(self):
        (self.root / 'src/auth.py').write_text(SOURCE + '\n# local edit\n', encoding='utf-8')
        self.request.write_text(self.run_plan('scout', 'request', 'locate', 'symbol=refresh_token',
                                              '--purpose', 'find it', '--include', 'src', ok=True).stdout,
                                encoding='utf-8')
        # Already modified before the run; a second edit keeps the same status letter.
        result = self.scout({'kind': 'write_repo', 'path': str(self.root / 'src/auth.py'), 'report': good_report()})
        self.assert_fallback(result, 'changed the working tree')
        self.assertIn('src/auth.py', result.stderr)

    def test_writes_to_the_scratch_copy_reject_the_report(self):
        result = self.scout({'kind': 'write_stage', 'report': good_report()})
        self.assert_fallback(result, 'wrote files')
        self.assertEqual(self.counters()['rejected'].get('provider_wrote'), 1)

    def test_missing_cli_falls_back(self):
        result = self.scout(path=self.empty)
        self.assert_fallback(result, 'agy is not on PATH')
        self.assertEqual(self.counters()['fallbacks'], 1)

    @unittest.skipUnless(os.name == 'nt', 'batch launchers exist only on Windows')
    def test_batch_launcher_is_refused(self):
        (self.empty / 'agy.cmd').write_text('@echo off\r\n', encoding='utf-8')
        self.assert_fallback(self.scout(path=self.empty), 'batch launcher')

    def test_disabled_or_never_set_up_is_refused_with_the_fix(self):
        self.run_plan('scout', 'disable', ok=True)
        result = self.scout()
        self.assert_fallback(result, 'disabled', 'plan scout setup')
        shutil.rmtree(self.root / '.coldsession-state')
        self.assert_fallback(self.scout(), 'not set up', 'plan scout setup')
        self.assertEqual(self.calls(), [])

    def test_cache_hit_skips_the_provider(self):
        self.scout(ok=True)
        result = self.scout({'kind': 'garbage'}, ok=True)
        self.assertIn('cache hit', result.stdout)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.counters()['cache_hits'], 1)


if __name__ == '__main__':
    unittest.main()
