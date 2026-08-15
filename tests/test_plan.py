import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "bin" / "plan"


def phase_text(*, rev=1, reviewed=None, ready=None, status="draft",
               workflow="1.4.0", findings="", tasks=None):
    tasks = tasks or {
        "T1": ([], "pending", ["src/a.py"]),
        "T2": ([], "pending", ["src/b.py"]),
    }
    meta = [
        "---",
        "phase: 01-test",
        f"rev: {rev}",
        f"status: {status}",
    ]
    if reviewed is not None:
        meta.append(f"reviewed: {reviewed}")
    if ready is not None:
        meta.append(f"ready: {ready}")
    meta += [f"workflow-rev: {workflow}", "tasks:"]
    for tid, (deps, task_status, files) in tasks.items():
        meta.append(
            f"  {tid}: {{deps: [{', '.join(deps)}], status: {task_status}, "
            f"files: [{', '.join(files)}]}}"
        )
    body = ["---", "", "# Phase 01 — test", ""]
    for tid in tasks:
        body += [
            f"## {tid} — test",
            "",
            "Goal: test",
            "Deliverables: test",
            "Acceptance Criteria: observable",
            "Verify: `python -V` exits 0",
            "",
        ]
    body += [
        "## Assumptions", "", "None.", "",
        "## Open questions", "", "None.", "",
        "## Out of scope", "", "None.", "",
        "## Findings", "", findings, "",
        "## Changelog", "",
    ]
    return "\n".join(meta + body) + "\n"


class PlanRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "plans").mkdir(parents=True)
        self.phase = self.root / "docs" / "plans" / "01-test.md"
        (self.root / "PLAN.md").write_text(
            "---\ncurrent: docs/plans/01-test.md\nworkflow-rev: 1.4.0\n---\n\n"
            "# Plan\n\n- [ ] Phase 01 — test — docs/plans/01-test.md\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def write_phase(self, **kwargs):
        self.phase.write_text(phase_text(**kwargs), encoding="utf-8")

    def run_plan(self, *args, ok=True):
        env = os.environ.copy()
        env["PLAN_ROOT"] = str(self.root)
        result = subprocess.run(
            [sys.executable, str(PLAN), *args],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if ok and result.returncode != 0:
            self.fail(f"plan {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
        return result

    def test_review_claim_requires_explicit_resume_and_cleans_up(self):
        self.write_phase()
        self.assertIn("begin review", self.run_plan("begin", "review").stdout)
        duplicate = self.run_plan("begin", "review", ok=False)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("/cs-review --resume", duplicate.stderr)
        self.assertIn("resume review", self.run_plan("begin", "review", "--resume").stdout)
        self.run_plan("finish", "review")
        text = self.phase.read_text(encoding="utf-8")
        self.assertIn("reviewed: 1", text)
        self.assertNotIn("active:", text)
        self.assertNotEqual(self.run_plan("begin", "review", ok=False).returncode, 0)

    def test_mismatched_stage_cannot_resume_another_claim(self):
        self.write_phase()
        self.run_plan("begin", "review")
        result = self.run_plan("begin", "approve", "--resume", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("review is active", result.stderr)
        self.assertIn("/cs-review --resume", result.stderr)

    def test_revise_bump_is_idempotent_and_review_precedes_open_findings(self):
        findings = (
            "F1 | High | Risk | T1 | open | first gap | change T1 line\n"
            "F2 | Medium | Risk | T2 | open | second gap | change T2 line"
        )
        self.write_phase(reviewed=1, findings=findings)
        self.run_plan("begin", "revise")
        self.assertIn("rev -> 2", self.run_plan("bump").stdout)
        self.assertIn("already 2", self.run_plan("bump").stdout)
        self.run_plan("resolve", "F1", "resolved", "T1 line now carries the fix")
        self.run_plan("finish", "revise")
        recommendation = self.run_plan("recommend").stdout
        self.assertTrue(recommendation.startswith("/cs-review"), recommendation)
        self.assertIn("rev: 2", self.phase.read_text(encoding="utf-8"))

    def test_approve_ready_marker_blocks_duplicate_check(self):
        self.write_phase(reviewed=1)
        self.run_plan("begin", "approve")
        self.run_plan("finish", "approve", "--pass")
        text = self.phase.read_text(encoding="utf-8")
        self.assertIn("ready: 1", text)
        self.assertIn("set status: approved", self.run_plan("recommend").stdout)
        self.assertNotEqual(self.run_plan("begin", "approve", ok=False).returncode, 0)

    def test_failed_approve_requires_persisted_gap_and_routes_to_revise(self):
        self.write_phase(reviewed=1)
        self.run_plan("begin", "approve")
        text = self.phase.read_text(encoding="utf-8").replace(
            "## Changelog",
            "F1 | High | Risk | T1 | open | residual risk | add mitigation to T1\n\n"
            "## Changelog",
        )
        self.phase.write_text(text, encoding="utf-8")
        self.run_plan("finish", "approve", "--fail")
        self.assertNotIn("active:", self.phase.read_text(encoding="utf-8"))
        self.assertTrue(self.run_plan("recommend").stdout.startswith("/cs-revise"))

    def test_parallel_build_claims_and_resume(self):
        self.write_phase(reviewed=1, ready=1, status="approved")
        self.run_plan("start", "T1")
        self.run_plan("start", "T2")
        duplicate = self.run_plan("start", "T1", ok=False)
        self.assertIn("--resume", duplicate.stderr)
        self.run_plan("start", "T1", "--resume")
        self.run_plan("brief", "T1")
        self.run_plan("done", "T1")
        self.assertIn("/cs-build T2 --resume", self.run_plan("recommend").stdout)
        self.run_plan("done", "T2")

    def test_build_blocker_demotes_phase_and_clears_readiness(self):
        self.write_phase(reviewed=1, ready=1, status="approved")
        self.run_plan("start", "T1")
        self.run_plan("block", "T1", "missing contract")
        text = self.phase.read_text(encoding="utf-8")
        self.assertIn("status: draft", text)
        self.assertNotIn("ready:", text)
        self.assertIn("status: blocked", text)
        text = text.replace(
            "## Changelog",
            "F1 | High | Risk | T1 | open | missing contract | add contract to T1\n\n"
            "## Changelog",
        )
        self.phase.write_text(text, encoding="utf-8")
        self.assertTrue(self.run_plan("recommend").stdout.startswith("/cs-revise"))

    def test_close_is_guarded_and_ticks_index(self):
        tasks = {
            "T1": ([], "done", ["src/a.py"]),
            "T2": ([], "done", ["src/b.py"]),
        }
        self.write_phase(reviewed=1, ready=1, status="approved", tasks=tasks)
        self.run_plan("begin", "close")
        self.assertNotEqual(self.run_plan("begin", "close", ok=False).returncode, 0)
        self.run_plan("begin", "close", "--resume")
        self.run_plan("finish", "close", "--pass")
        self.assertIn("status: closed", self.phase.read_text(encoding="utf-8"))
        self.assertIn("- [x] Phase 01", (self.root / "PLAN.md").read_text(encoding="utf-8"))
        self.assertNotEqual(self.run_plan("begin", "close", ok=False).returncode, 0)

    def test_legacy_13_approved_phase_does_not_require_ready(self):
        self.write_phase(reviewed=1, status="approved", workflow="1.3.0")
        self.assertEqual(self.run_plan("lint").returncode, 0)

    def test_new_14_approved_phase_requires_ready(self):
        self.write_phase(reviewed=1, status="approved")
        result = self.run_plan("lint", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("E22", result.stdout)


class WorkflowContractTest(unittest.TestCase):
    def test_objective_template_is_planning_ready(self):
        text = (ROOT / "templates" / "OBJECTIVE.md").read_text(encoding="utf-8")
        for heading in (
            "## Problem", "## Value proposition", "## Users and primary journey",
            "## MVP", "## Out of scope", "## Constraints",
            "## Success criteria", "## Assumptions", "## Open questions",
        ):
            self.assertIn(heading, text)
        self.assertIn("status: ready", text)
        self.assertIn("None.", text)

    def test_plan_contract_never_reads_objective_after_plan_exists(self):
        text = (ROOT / "commands" / "cs-plan.md").read_text(encoding="utf-8")
        self.assertIn("Require root `OBJECTIVE.md` with `status: ready`", text)
        marker = text.index("### PLAN.md exists")
        boundary = text.index("## Plan quality")
        existing_plan_branch = text[marker:boundary]
        self.assertIn("Do not open, search, quote, or otherwise read `OBJECTIVE.md`", existing_plan_branch)
        self.assertIn("Never rewrite an active phase", existing_plan_branch)


if __name__ == "__main__":
    unittest.main()
