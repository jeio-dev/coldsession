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

import shutil
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
