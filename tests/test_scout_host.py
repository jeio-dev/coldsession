"""Scout as the host sees it (#21): the command text, `plan scout status`, and inline runs.

Provider calls go to the stub `agy` from test_scout_run. No network, model, or real provider CLI.
"""
import json
import os
import re
import subprocess
import sys
import unittest

from test_plan import clean_env
from test_scout import ROOT, module
import test_scout_run
from test_scout_run import GIT

SOFT_RULE = ("Scout (experimental): when orientation would need more than about 5 files, run\n"
             "`.claude/bin/plan scout status` first, and only if it exits 0, follow what it prints.\n")
# Commands whose own instructions call for broad orientation reading. Groundwork
# starts from an empty repository, Revise works from findings that name their
# targets, Build reads its brief, and the judging stages read for themselves.
EXPLORING = ('cs-define', 'cs-plan', 'cs-issue')


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


class ScoutCommandTextTest(unittest.TestCase):
    def test_soft_rule_is_one_conditional_line_in_exploring_commands_only(self):
        for path in sorted((ROOT / 'commands').glob('cs-*.md')):
            count = text(path).count(SOFT_RULE)
            self.assertEqual(count, 1 if path.stem in EXPLORING else 0, path.stem)
            if path.stem not in EXPLORING and path.stem != 'cs-scout':
                self.assertNotIn('scout', text(path).lower(), path.stem)

    def test_command_carries_the_report_rules(self):
        body = text(ROOT / 'commands/cs-scout.md')
        for phrase in ('## Run a request', '## Use the report',  # named by plan scout status
                       '.claude/bin/plan scout status', '.claude/bin/plan scout run KIND NAME=VALUE...',
                       'locate symbol=NAME', 'trace from=A to=B', 'inventory symbol=NAME',
                       'are fact', 'Do not re-explore them', 'working assumptions',
                       'Read every `read next` range yourself before editing',
                       'explore natively or send one narrower request',
                       'orientation only', '.coldsession-state/scout/', 'E36',
                       'run_in_background', 'Otherwise run it in the foreground',
                       'active Build claim', 'cite only files in the task',
                       'scout unavailable (<reason>); explore natively',
                       'never run setup yourself'):
            self.assertIn(phrase, body)
        self.assertNotIn('--request', body, 'hosts run inline requests and never write a request file')

    def test_codex_skill_follows_the_same_command(self):
        skill = text(ROOT / 'skills/cs-scout/SKILL.md')
        self.assertIn('name: cs-scout', skill)
        self.assertIn('Read `.agents/coldsession/commands/cs-scout.md` completely', skill)
        self.assertIn('$ARGUMENTS', skill)
        self.assertIn('Never run `plan scout setup` yourself', skill)
        self.assertIn('$cs-scout', text(ROOT / 'skills/cs-scout/agents/openai.yaml'))

    def test_both_harnesses_install_identical_instructions(self):
        installer = module('installer_scout_host', ROOT / 'bin/cs_install.py')
        for windows in (False, True):
            files = installer.bundle(ROOT, ROOT, 'both', windows=windows)
            claude = files['.claude/commands/cs-scout.md'].decode('utf-8')
            codex = files['.agents/coldsession/commands/cs-scout.md'].decode('utf-8')
            self.assertIn('.agents/skills/cs-scout/SKILL.md', files)
            self.assertIn('.agents/skills/cs-scout/agents/openai.yaml', files)
            runtime = '.claude/bin/plan.cmd' if windows else '.claude/bin/plan'
            self.assertIn(runtime + ' scout run', claude)
            self.assertEqual(claude.replace('.claude/bin/plan', '.agents/coldsession/bin/plan'), codex)


class ScoutHostTest(unittest.TestCase):
    """The stub provider fixture from test_scout_run, with scout set up and `src` in scope.

    Borrowed through the module, not imported by name, so discovery does not run that suite twice.
    """
    setUp = test_scout_run.ScoutRunTest.setUp
    git = test_scout_run.ScoutRunTest.git
    run_plan = test_scout_run.ScoutRunTest.run_plan
    calls = test_scout_run.ScoutRunTest.calls
    assert_fallback = test_scout_run.ScoutRunTest.assert_fallback

    def inline(self, *extra, ok=None, path=None, as_json=False):
        args = ['scout', 'run', 'locate', 'symbol=refresh_token', '--purpose', 'find it',
                '--include', 'src', '--include', 'private', *extra] + (['--json'] if as_json else [])
        return self.run_plan(*args, ok=ok, path=path)

    def assert_off(self, reason, path=None):
        result = self.run_plan('scout', 'status', path=path)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, f'scout off ({reason}); explore natively\n')
        data = json.loads(self.run_plan('scout', 'status', '--json', path=path).stdout)
        self.assertEqual((data['available'], data['reason'], data['guide']), (False, reason, None))

    def test_status_when_on_points_to_the_command_sections(self):
        result = self.run_plan('scout', 'status', ok=True)
        first, second = result.stdout.splitlines()
        self.assertEqual(first, 'scout on (experimental): agy, model provider default, timeout 180s')
        guide = re.search(r'read (.+) and follow', second).group(1)
        self.assertTrue(os.path.samefile(guide, ROOT / 'commands/cs-scout.md'))
        body = text(ROOT / 'commands/cs-scout.md')
        for section in re.findall(r'"([^"]+)"', second):
            self.assertIn('## ' + section + '\n', body)
        data = json.loads(self.run_plan('scout', 'status', '--json', ok=True).stdout)
        self.assertEqual((data['available'], data['provider'], data['reason']), (True, 'agy', None))
        self.assertEqual(self.calls(), [], 'status never calls the provider for a request')

    def test_status_is_off_when_not_set_up_disabled_missing_or_invalid(self):
        self.assert_off('agy is not on PATH', path=self.empty)
        self.run_plan('scout', 'disable', ok=True)
        self.assert_off('disabled')
        config = self.root / '.coldsession-state/scout/config.json'
        config.write_text('{"enabled": "yes"}', encoding='utf-8')
        result = self.run_plan('scout', 'status')
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stdout, r'^scout off \(invalid scout config: .+\); explore natively\n$')
        config.unlink()
        self.assert_off('not set up')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')

    def test_installed_status_names_the_installed_command(self):
        installer = module('installer_scout_status', ROOT / 'bin/cs_install.py')
        for relative, data in installer.bundle(ROOT, self.root, 'both', windows=False).items():
            if relative.startswith(('.claude/', '.agents/')):
                target = self.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        for runtime, guide in (('.claude/bin/plan', '.claude/commands/cs-scout.md'),
                               ('.agents/coldsession/bin/plan', '.agents/coldsession/commands/cs-scout.md')):
            env = clean_env(PLAN_ROOT=str(self.root),
                            PATH=os.pathsep.join((str(self.bin), os.path.dirname(GIT))))
            result = subprocess.run([sys.executable, str(self.root / runtime), 'scout', 'status', '--json'],
                                    cwd=self.root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['guide'], guide)
            self.assertTrue((self.root / guide).is_file())

    def test_inline_run_matches_a_request_file_and_leaves_the_tree_clean(self):
        result = self.inline(ok=True)
        self.assertIn('scout locate: answered (orientation only', result.stdout)
        self.assertIn('E1 src/auth.py:1-2', result.stdout)
        self.assertIn('cache stored', result.stdout)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        # The same request from a file is the same cache entry: no second call.
        cached = self.run_plan('scout', 'run', '--request', str(self.request), ok=True)
        self.assertIn('cache hit', cached.stdout)
        self.assertEqual(len(self.calls()), 1)
        data = json.loads(self.inline(as_json=True, ok=True).stdout)
        self.assertTrue(data['accepted'])
        self.assertEqual(data['cache'], 'hit')

    def test_inline_run_falls_back_in_one_line_when_scout_is_off(self):
        self.run_plan('scout', 'disable', ok=True)
        self.assert_fallback(self.inline(), 'scout is disabled')
        (self.root / '.coldsession-state/scout/config.json').unlink()
        self.assert_fallback(self.inline(), 'not set up')
        self.assertEqual(self.calls(), [])

    def test_inline_run_is_validated_like_a_request(self):
        for args in (['scout', 'run', 'locate', 'symbol=x'],  # no purpose
                     ['scout', 'run', 'locate', 'symbol=x', '--purpose', 'p', '--request', str(self.request)],
                     ['scout', 'run', 'guess', 'symbol=x', '--purpose', 'p'],
                     ['scout', 'run', 'locate', 'name=x', '--purpose', 'p'],
                     ['scout', 'status', 'extra']):
            result = self.run_plan(*args)
            self.assertNotEqual(result.returncode, 0, args)
            self.assertNotIn('scout unavailable', result.stdout, args)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
