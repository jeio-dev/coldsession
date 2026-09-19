"""Tests the prompt-eval grading logic without invoking a model.

evals/run.py drives the real `claude` CLI, which costs tokens and needs live
credentials -- not something the standard test suite should do. What can be
tested for free is the harness itself: given a fixture project and a
hand-built pre/post-run state standing in for what a real `claude -p` run
would have produced, does each fixture's expect.py grade correctly? Every
"catches" test below reproduces the exact regression its fixture exists to
catch (see evals/README.md) and asserts the grader actually flags it, so a
broken grader -- one that would let a regression "ship green" -- fails here
before it ever reaches evals/run.py.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import os
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"

sys.path.insert(0, str(EVALS))
import lib as evals_lib  # noqa: E402


def _lay_down_fixture(name, tmp):
    """Copy a fixture's project/ files into `tmp` and place the plan binary.

    Skips the real installer (install.sh/.ps1) for speed and platform
    independence: EvalContext.plan() invokes `.claude/bin/plan` via
    `sys.executable`, so only the file needs to be in place, not a full
    install.
    """
    src = evals_lib.FIXTURES / name / "project"
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        dest = tmp / item.relative_to(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, dest)
    plan_bin_dir = tmp / ".claude" / "bin"
    plan_bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "bin" / "plan", plan_bin_dir / "plan")


NEW_PHASE_TEXT = (
    "---\n"
    "phase: 02-sync-durability\n"
    "rev: 1\n"
    "status: draft\n"
    "workflow-rev: 1.4.0\n"
    "tasks:\n"
    "  T1: {deps: [], status: pending, files: [src/sync/retry.ts]}\n"
    "---\n\n"
    "# Phase 02 — sync durability\n\n"
    "## T1 — retry\n\n"
    "Goal: retry a failed sync send.\n"
    "Deliverables: `src/sync/retry.ts`.\n"
    "Acceptance Criteria: a failed send is retried with backoff.\n"
    "Verify: `npm test -- retry` exits 0\n\n"
    "## Assumptions\n\nNone.\n\n"
    "## Open questions\n\nNone.\n\n"
    "## Out of scope\n\nNone.\n\n"
    "## Findings\n\n\n\n"
    "## Changelog\n\n"
)


class EvalHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_fixtures_are_discovered(self):
        names = evals_lib.list_fixtures()
        for expected in (
            "review-writes-findings",
            "approve-refuses-to-set-status",
            "plan-does-not-reread-objective",
        ):
            self.assertIn(expected, names)

    def test_evaluation_isolates_session_plugins_and_orchestration(self):
        with mock.patch.dict(os.environ, {'ORCA_WORKTREE_ID': 'real-workspace',
                                          'CLAUDE_CODE_SESSION_ID': 'real-session',
                                          'CLAUDE_PLUGIN_ROOT': 'inherited-plugin',
                                          'CODEX_THREAD_ID': 'real-thread',
                                          'CS_WORKER_ASSIGNMENT': 'worker'}):
            env = evals_lib.isolated_env(self.tmp)
        for key in ('ORCA_WORKTREE_ID', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_PLUGIN_ROOT',
                    'CODEX_THREAD_ID', 'CS_WORKER_ASSIGNMENT'):
            self.assertNotIn(key, env)
        self.assertTrue(Path(env['CLAUDE_CONFIG_DIR']).is_relative_to(self.tmp))

    def test_evaluation_redacts_credentials_but_keeps_token_counts(self):
        record = evals_lib.redact({'api_key': 'secret-value', 'usage': {'input_tokens': 42},
                                  'output': 'token=private-token'})
        self.assertNotIn('secret-value', str(record))
        self.assertNotIn('private-token', str(record))
        self.assertEqual(record['usage']['input_tokens'], 42)
        self.assertEqual(evals_lib.redact({'tokens': {'input_tokens': 42}})['tokens']['input_tokens'], 42)

    def test_gateway_settings_pass_through_and_its_key_is_redacted(self):
        with mock.patch.dict(os.environ, {'ANTHROPIC_BASE_URL': 'https://openrouter.ai/api',
                                          'ANTHROPIC_AUTH_TOKEN': 'sk-or-v1-abcdef0123456789',
                                          'ANTHROPIC_MODEL': 'vendor/model'}):
            env = evals_lib.isolated_env(self.tmp)
        self.assertEqual(env['ANTHROPIC_BASE_URL'], 'https://openrouter.ai/api')
        self.assertEqual(env['ANTHROPIC_MODEL'], 'vendor/model')
        self.assertNotIn('sk-or-v1-abcdef0123456789', str(evals_lib.redact(
            {'auth_token': 'sk-or-v1-abcdef0123456789', 'output': 'failed with sk-or-v1-abcdef0123456789'})))

    def test_every_fixture_has_a_loadable_expect(self):
        """Nothing runs evals/run.py automatically, so a fixture broken by a
        rename would stay broken until someone finally ran it by hand. This
        catches that for free: load_expect() raises FixtureError for a
        missing or grade-less expect.py."""
        names = evals_lib.list_fixtures()
        self.assertTrue(names)
        for name in names:
            evals_lib.load_expect(name)

    def test_review_fixture_starts_lint_clean(self):
        _lay_down_fixture("review-writes-findings", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        result = ctx.plan("lint")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_review_fixture_grades_a_compliant_run_clean(self):
        _lay_down_fixture("review-writes-findings", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        ctx.plan("begin", "review", ok=True)

        phase = self.tmp / "docs" / "plans" / "01-sync.md"
        text = phase.read_text(encoding="utf-8")
        marker = ("     No pipes inside a description or fix; the parser "
                  "splits on them. -->")
        self.assertIn(marker, text)
        text = text.replace(
            marker,
            marker + "\n\n"
            "F1 | Critical | Task ordering | T2 | open | "
            "T2 needs schema.ts from T1 but has no dep or files entry for it | "
            "add T1 to T2 deps and schema.ts to T2 files",
        )
        phase.write_text(text, encoding="utf-8")
        ctx.plan("finish", "review", ok=True)
        ctx.plan("begin", "revise", ok=True)
        ctx.plan("bump", ok=True)
        text = phase.read_text(encoding="utf-8")
        text = text.replace(
            "T2: {deps: [], status: pending, files: [src/sync/queue.ts]}",
            "T2: {deps: [T1], status: pending, files: [src/sync/queue.ts, src/db/schema.ts]}",
        )
        phase.write_text(text, encoding="utf-8")
        ctx.plan("resolve", "F1", "resolved",
                 "T2 now depends on T1 and includes src/db/schema.ts", ok=True)
        ctx.plan("finish", "revise", ok=True)

        grade = evals_lib.load_expect("review-writes-findings")
        self.assertEqual(grade(ctx), [])

    def test_review_fixture_catches_a_review_that_writes_no_findings(self):
        """The exact regression the plan calls out: a reworded cs-review.md
        that quietly stops writing findings must not ship green."""
        _lay_down_fixture("review-writes-findings", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        ctx.plan("begin", "review", ok=True)
        ctx.plan("finish", "review", ok=True)

        grade = evals_lib.load_expect("review-writes-findings")
        failures = grade(ctx)
        self.assertTrue(failures)
        self.assertTrue(any("no findings" in f.lower() for f in failures), failures)

    def test_review_fixture_catches_a_review_that_only_recommends_revise(self):
        _lay_down_fixture("review-writes-findings", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        ctx.plan("begin", "review", ok=True)
        phase = self.tmp / "docs" / "plans" / "01-sync.md"
        text = phase.read_text(encoding="utf-8")
        text = text.replace(
            "## Findings",
            "## Findings\n\nF1 | Critical | Task ordering | T2 | open | "
            "T2 needs T1 | add T1 to T2 deps",
        )
        phase.write_text(text, encoding="utf-8")
        ctx.plan("finish", "review", ok=True)

        failures = evals_lib.load_expect("review-writes-findings")(ctx)
        self.assertTrue(any("automatic Revise" in failure for failure in failures), failures)

    def test_approve_fixture_grades_a_compliant_pass_clean(self):
        _lay_down_fixture("approve-refuses-to-set-status", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        ctx.plan("begin", "approve", ok=True)
        ctx.plan("finish", "approve", "--pass", ok=True)

        grade = evals_lib.load_expect("approve-refuses-to-set-status")
        self.assertEqual(grade(ctx), [])

    def test_approve_fixture_catches_status_set_to_approved(self):
        """The exact regression the fixture exists for: /cs-approve must
        never flip status to approved itself."""
        _lay_down_fixture("approve-refuses-to-set-status", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp)
        ctx.plan("begin", "approve", ok=True)
        ctx.plan("finish", "approve", "--pass", ok=True)

        phase = self.tmp / "docs" / "plans" / "01-sync.md"
        text = phase.read_text(encoding="utf-8")
        self.assertIn("status: draft", text)
        phase.write_text(text.replace("status: draft", "status: approved", 1),
                         encoding="utf-8")

        grade = evals_lib.load_expect("approve-refuses-to-set-status")
        failures = grade(ctx)
        self.assertTrue(failures)
        self.assertTrue(any("approved itself" in f for f in failures), failures)

    def test_plan_fixture_grades_a_compliant_run_clean(self):
        _lay_down_fixture("plan-does-not-reread-objective", self.tmp)
        (self.tmp / "docs" / "plans" / "02-sync-durability.md").write_text(
            NEW_PHASE_TEXT, encoding="utf-8"
        )
        plan_md = self.tmp / "PLAN.md"
        plan_md.write_text(
            plan_md.read_text(encoding="utf-8").replace(
                "current: docs/plans/01-sync.md",
                "current: docs/plans/02-sync-durability.md",
            ),
            encoding="utf-8",
        )
        ctx = evals_lib.EvalContext(tmp=self.tmp, events=[])

        grade = evals_lib.load_expect("plan-does-not-reread-objective")
        self.assertEqual(grade(ctx), [])

    def test_plan_fixture_catches_a_transcript_that_reads_objective(self):
        _lay_down_fixture("plan-does-not-reread-objective", self.tmp)
        (self.tmp / "docs" / "plans" / "02-sync-durability.md").write_text(
            NEW_PHASE_TEXT, encoding="utf-8"
        )
        events = [{
            "message": {"content": [
                {"type": "tool_use", "name": "Read",
                 "input": {"file_path": "OBJECTIVE.md"}},
            ]},
        }]
        ctx = evals_lib.EvalContext(tmp=self.tmp, events=events)

        grade = evals_lib.load_expect("plan-does-not-reread-objective")
        failures = grade(ctx)
        self.assertTrue(failures)
        self.assertTrue(any("OBJECTIVE.md" in f for f in failures), failures)

    def test_plan_fixture_catches_missing_new_phase_file(self):
        _lay_down_fixture("plan-does-not-reread-objective", self.tmp)
        ctx = evals_lib.EvalContext(tmp=self.tmp, events=[])

        grade = evals_lib.load_expect("plan-does-not-reread-objective")
        failures = grade(ctx)
        self.assertTrue(failures)
        self.assertTrue(any("no docs/plans/02" in f for f in failures), failures)


import scout as scout_eval  # noqa: E402

# The answers each scout scenario's grader must accept, from the pinned revision.
SCOUT_ANSWERS = {
    "evidence-stale-reasons": {
        "function": "evidence_failure_reasons",
        "reasons": ["evidence_missing", "spec_changed", "inputs_changed", "checks_changed", "verification_failed"]},
    "installed-claude-hooks": {
        "hooks": [{"event": "PreToolUse", "guard": "write", "matcher": "Write|Edit|apply_patch|MultiEdit"},
                  {"event": "UserPromptSubmit", "guard": "stage", "matcher": None},
                  {"event": "PostToolUse", "guard": "lint", "matcher": "Edit|Write|MultiEdit|apply_patch"},
                  {"event": "PreToolUse", "guard": "read", "matcher": "Read|Grep"}],
        "bash_guarded": False},
    "installer-line-endings": {
        "normalizer": "canonical_text", "callers": ["same_text", "matches_hash", "preview", "codex_hook_hash"]},
    "issue-adoption": {
        "adoption": "issue_adoptions", "body_hash": "issue_body_sha256", "entry_guard": "_issue_entry_guard",
        "url_case_insensitive": True},
    "build-read-set": {
        "function": "read_set", "commands": ["guard", "brief"], "strict_includes_dependency_files": False},
}
SCOUT_WRONG = {
    "evidence-stale-reasons": {"reasons": ["evidence_missing", "spec_changed", "inputs_changed", "verification_failed"]},
    "installed-claude-hooks": {"bash_guarded": True},
    "installer-line-endings": {"callers": ["same_text", "matches_hash"]},
    "issue-adoption": {"url_case_insensitive": False},
    "build-read-set": {"strict_includes_dependency_files": True},
}


class ScoutScenarioTest(unittest.TestCase):
    """The paired scout benchmark: scenario shape, graders, and the decision rule, without a model."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cs-scout-eval-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.scenarios = {p.stem: scout_eval.load_scenario(p) for p in sorted(scout_eval.SCENARIOS.glob("*.json"))}

    def passes(self, scenario):
        return [check["exit"] == 0 for check in scout_eval.grade(scenario, self.tmp)]

    def test_benchmark_has_five_to_ten_pinned_exploration_scenarios(self):
        self.assertTrue(5 <= len(self.scenarios) <= 10, sorted(self.scenarios))
        for name, scenario in self.scenarios.items():
            self.assertEqual(scenario["id"], name)
            self.assertIn(scenario["exploration"], ("locate", "trace", "inventory"))
            self.assertRegex(scenario["source"]["rev"], r"^[0-9a-f]{40}$")
            self.assertTrue(scenario["derived_from"])
        self.assertEqual(set(self.scenarios) - {"stale-verify-fix"}, set(SCOUT_ANSWERS))

    def test_identical_prompt_ends_with_the_soft_rule(self):
        for scenario in self.scenarios.values():
            text = scout_eval.prompt(scenario)
            self.assertTrue(text.startswith(scenario["task"]))
            self.assertIn("scout status`, and only if it exits 0", text)

    def test_permissions_allow_only_scout_commands_and_writable_files(self):
        rules = scout_eval.allowed_tools(self.scenarios["stale-verify-fix"])
        self.assertEqual(rules, [f"Bash({scout_eval.plan_command()} scout:*)", "Edit(bin/plan)", "Write(bin/plan)"])
        self.assertFalse(any(rule in ("Bash", "Edit", "Write") for rule in rules))

    def test_answer_graders_accept_the_truth_and_reject_a_wrong_answer(self):
        for name, answer in SCOUT_ANSWERS.items():
            with self.subTest(name):
                (self.tmp / "ANSWER.json").write_text(json.dumps(answer), encoding="utf-8")
                self.assertTrue(all(self.passes(self.scenarios[name])))
                (self.tmp / "ANSWER.json").write_text(json.dumps(dict(answer, **SCOUT_WRONG[name])), encoding="utf-8")
                self.assertFalse(all(self.passes(self.scenarios[name])))
                (self.tmp / "ANSWER.json").unlink()
                self.assertFalse(any(self.passes(self.scenarios[name])))

    def test_fix_grader_catches_the_injected_regression(self):
        scenario = self.scenarios["stale-verify-fix"]
        rev = subprocess.run(["git", "show", scenario["source"]["rev"] + ":bin/plan"], cwd=ROOT,
                             capture_output=True, check=False)
        # A shallow CI checkout lacks the pinned revision; the hunk is unchanged in HEAD.
        text = (rev.stdout if rev.returncode == 0 else (ROOT / "bin" / "plan").read_bytes()).decode("utf-8")
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "plan").write_bytes(text.encode("utf-8"))
        self.assertEqual(self.passes(scenario), [True, True])
        patch = scenario["patches"][0]
        self.assertEqual(text.count(patch["old"]), 1)
        (self.tmp / "bin" / "plan").write_bytes(text.replace(patch["old"], patch["new"]).encode("utf-8"))
        self.assertEqual(self.passes(scenario), [False, True])

    def test_changed_files_ignore_harness_state_only(self):
        scout_eval.git(self.tmp, "init", "-q")
        (self.tmp / "kept.txt").write_text("a", encoding="utf-8")
        scout_eval.git(self.tmp, "add", "-A")
        scout_eval.git(self.tmp, "commit", "-q", "-m", "base")
        for name in ("ANSWER.json", ".coldsession-state/scout/stats.json", ".eval-config/x", "src/new.py"):
            (self.tmp / name).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / name).write_text("x", encoding="utf-8")
        (self.tmp / "kept.txt").write_text("b", encoding="utf-8")
        self.assertEqual(scout_eval.changed_files(self.tmp), ["ANSWER.json", "kept.txt", "src/new.py"])

    def run_record(self, scenario, arm, tokens, correct=True, **scout):
        return {"scenario": scenario, "arm": arm, "host_tokens": tokens, "correct": correct, "failures": [],
                "cost_usd": 0.1, "agent_seconds": 60 if arm == "native" else scout.pop("seconds", 50),
                "scout": dict({"runs": 0, "accepted": 0, "fallbacks": 0, "cache_hits": 0, "rejected": {}}, **scout)
                if arm != "native" else None}

    def test_decision_rule_keeps_scout_only_with_savings_and_few_rejections(self):
        runs = [self.run_record("a", "native", 1000), self.run_record("b", "native", 2000),
                self.run_record("a", "scout:fast", 700, accepted=4, rejected={"snippet_mismatch": 1}, seconds=40),
                self.run_record("b", "scout:fast", 1500, accepted=5),
                self.run_record("a", "scout:slow", 600, accepted=5, seconds=90),
                self.run_record("b", "scout:slow", 1400, accepted=5, seconds=90),
                self.run_record("a", "scout:noisy", 500, accepted=3, rejected={"invalid_shape": 2}),
                self.run_record("b", "scout:noisy", 900, accepted=4)]
        summary = scout_eval.summarize({"runs": runs})
        self.assertAlmostEqual(summary["arms"]["scout:fast"]["reduction"], 0.2667, places=3)
        self.assertAlmostEqual(summary["arms"]["scout:fast"]["scout"]["rejection_rate"], 0.1)
        self.assertEqual(summary["arms"]["scout:fast"]["verdict"], "passes")
        self.assertEqual(summary["arms"]["scout:noisy"]["verdict"], "fails")  # 2 of 9 reports rejected
        self.assertEqual(summary["fastest_passing_arm"], "scout:fast")
        self.assertEqual(summary["verdict"], "keep")

    def test_decision_rule_fails_on_lower_correctness_and_reports_unknowns(self):
        runs = [self.run_record("a", "native", 1000), self.run_record("a", "scout:x", 500, correct=False, accepted=5)]
        self.assertEqual(scout_eval.summarize({"runs": runs})["verdict"], "fails the rule")
        runs = [self.run_record("a", "native", 1000), self.run_record("a", "scout:x", None, accepted=5)]
        self.assertEqual(scout_eval.summarize({"runs": runs})["verdict"], "insufficient evidence")
        runs = [self.run_record("a", "native", 1000), self.run_record("a", "scout:x", 500, fallbacks=1)]
        summary = scout_eval.summarize({"runs": runs})
        self.assertIsNone(summary["arms"]["scout:x"]["scout"]["rejection_rate"])
        self.assertEqual(summary["verdict"], "insufficient evidence")


if __name__ == "__main__":
    unittest.main()
