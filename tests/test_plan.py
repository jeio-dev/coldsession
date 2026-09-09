import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "bin" / "plan"
BASH = shutil.which("bash")
SH = shutil.which("sh") or BASH
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


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

    def run_guard(self, *args, payload=None, root=None, session_dir=None):
        """A hook call: the event JSON on stdin, the decision in the exit code."""
        env = os.environ.copy()
        env["PLAN_ROOT"] = str(root or self.root)
        env["PLAN_SESSION_DIR"] = str(session_dir or (self.root / ".sessions"))
        return subprocess.run(
            [sys.executable, str(PLAN), "guard", *args],
            input="" if payload is None else json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

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

    def test_lint_warns_when_agents_md_is_over_budget(self):
        self.write_phase()
        (self.root / "AGENTS.md").write_text(
            "\n".join(f"line {i}" for i in range(61)) + "\n", encoding="utf-8")
        result = self.run_plan("lint")
        self.assertIn("W06", result.stdout)

    def test_lint_does_not_warn_when_agents_md_is_within_budget(self):
        self.write_phase()
        (self.root / "AGENTS.md").write_text(
            "\n".join(f"line {i}" for i in range(60)) + "\n", encoding="utf-8")
        result = self.run_plan("lint")
        self.assertNotIn("W06", result.stdout)

    def test_lint_does_not_warn_with_no_agents_md(self):
        self.write_phase()
        result = self.run_plan("lint")
        self.assertNotIn("W06", result.stdout)

    def test_metrics_fails_open_with_no_plan_state(self):
        with tempfile.TemporaryDirectory() as empty_root:
            env = os.environ.copy()
            env["PLAN_ROOT"] = empty_root
            result = subprocess.run(
                [sys.executable, str(PLAN), "metrics"],
                text=True, capture_output=True, env=env, check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_metrics_scans_every_phase_and_reports_indicators(self):
        findings = (
            "F1 | High | Risk | T1 | resolved | first gap | change T1 line\n"
            "F2 | Medium | Risk | T2 | accepted | second gap | acceptable risk"
        )
        tasks = {
            "T1": ([], "done", ["src/a.py"]),
            "T2": ([], "blocked", ["src/b.py"]),
        }
        self.write_phase(rev=2, reviewed=2, ready=2, status="closed",
                          findings=findings, tasks=tasks)
        second = self.root / "docs" / "plans" / "02-other.md"
        second.write_text(phase_text(rev=1, reviewed=1, ready=1, status="approved"),
                           encoding="utf-8")

        out = self.run_plan("metrics").stdout
        self.assertIn("phases   2 scanned (1 closed, 1 approved, 0 draft)", out)
        self.assertIn("revisions to approval   avg 0.5 (2 phase(s))", out)
        self.assertIn("first-pass approve rate 50% (1 of 2)", out)
        self.assertIn("tasks blocked           1 total across 1 of 2 phase(s)", out)
        self.assertIn("review rounds           avg 1.5 (2 phase(s))", out)
        self.assertIn("findings by severity    High 1, Medium 1 (2 total)", out)
        self.assertIn("findings reopened       0 (across 1 closed phase(s))", out)
        self.assertIn("resolved vs accepted    1 resolved, 1 accepted (50% resolved)", out)
        self.assertIn("phase cycle time        n/a", out)

    def test_metrics_does_not_read_the_current_phase_index(self):
        """metrics must not go through read_phase(read_index()) like every
        other subcommand -- it fails open even when PLAN.md's `current:`
        pointer is dangling, as long as docs/plans/ itself has phase files."""
        (self.root / "PLAN.md").write_text(
            "---\ncurrent: docs/plans/missing.md\nworkflow-rev: 1.4.0\n---\n\n"
            "# Plan\n\n- [ ] Phase 01 -- test -- docs/plans/missing.md\n",
            encoding="utf-8",
        )
        self.write_phase()
        result = self.run_plan("metrics")
        self.assertIn("phases   1 scanned", result.stdout)


    # ------------------------------------------------------------- guard

    def test_guard_fails_open_with_no_plan_state(self):
        """The highest-risk regression in the hooks: guard runs on every
        prompt and every file tool call, including in repositories that have
        never heard of coldsession. All four gates must exit 0 in silence."""
        with tempfile.TemporaryDirectory() as empty_root:
            for args in (("read", "somefile"), ("write", "somefile"),
                         ("lint", "somefile"),
                         ("stage", "/cs-review", "--session", "s1")):
                result = self.run_guard(*args, root=empty_root,
                                        session_dir=Path(empty_root) / ".sessions")
                self.assertEqual(result.returncode, 0, f"guard {args} denied")
                self.assertEqual(result.stderr, "", f"guard {args} was not silent")

    def test_guard_stage_fails_open_across_a_whole_session_with_no_plan_state(self):
        """The cold-session gate only ever denies on the *second* command, so
        checking one command at a time -- which is all the test above did --
        can never reach the denial. A repository that never adopted
        coldsession has to be able to run the entire sequence untouched."""
        with tempfile.TemporaryDirectory() as empty_root:
            sessions = Path(empty_root) / ".sessions"
            for prompt in ("/cs-plan", "/cs-revise", "/cs-review",
                           "/cs-approve", "/cs-close"):
                result = self.run_guard("stage", prompt, "--session", "one",
                                        root=empty_root, session_dir=sessions)
                self.assertEqual(result.returncode, 0,
                                 f"{prompt} denied with no plan state: {result.stderr}")
                self.assertEqual(result.stderr, "", prompt)

    def test_guard_stage_fails_open_when_plan_state_is_unreadable(self):
        """Absent is not the only unclear state. A dangling `current:` pointer
        and a phase file that will not parse are equally no basis to refuse."""
        self.write_phase()
        self.run_guard("stage", "/cs-plan", "--session", "dangling")
        (self.root / "PLAN.md").write_text(
            "---\ncurrent: docs/plans/missing.md\nworkflow-rev: 1.4.0\n---\n",
            encoding="utf-8")
        blocked = self.run_guard("stage", "/cs-review", "--session", "dangling")
        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertEqual(blocked.stderr, "")

        self.run_guard("stage", "/cs-plan", "--session", "unreadable")
        (self.root / "PLAN.md").write_text("not frontmatter at all\n", encoding="utf-8")
        unreadable = self.run_guard("stage", "/cs-review", "--session", "unreadable")
        self.assertEqual(unreadable.returncode, 0, unreadable.stderr)
        self.assertEqual(unreadable.stderr, "")

    def test_guard_fails_open_on_a_dangling_current_pointer(self):
        self.write_phase(tasks={"T1": ([], "in_progress", ["src/a.py"])})
        (self.root / "PLAN.md").write_text(
            "---\ncurrent: docs/plans/missing.md\nworkflow-rev: 1.4.0\n---\n",
            encoding="utf-8")
        self.assertEqual(self.run_guard("read", "src/anything.py").returncode, 0)

    def test_guard_bounds_reads_to_the_in_progress_brief(self):
        self.write_phase(status="approved", ready=1, reviewed=1, tasks={
            "T1": ([], "done", ["src/schema.py"]),
            "T2": (["T1"], "in_progress", ["src/queue.py"]),
            "T3": ([], "pending", ["src/worker.py"]),
        })
        for allowed in ("AGENTS.md", "PLAN.md", "src/schema.py", "src/queue.py",
                        "docs/plans/01-test.md", "docs/plans/01-test.log.md"):
            self.assertEqual(self.run_guard("read", allowed).returncode, 0, allowed)

        denied = self.run_guard("read", "src/worker.py")
        self.assertEqual(denied.returncode, 2)
        self.assertIn("E23", denied.stderr)
        self.assertIn("T2", denied.stderr)

    def test_guard_allows_the_union_of_every_in_progress_task(self):
        """plan next --parallel runs two build terminals at once and a hook
        cannot tell which session owns which task, so the union is the
        narrowest set that never fires a false positive."""
        self.write_phase(status="approved", ready=1, reviewed=1, tasks={
            "T1": ([], "in_progress", ["src/a.py"]),
            "T2": ([], "in_progress", ["src/b.py"]),
        })
        self.assertEqual(self.run_guard("read", "src/a.py").returncode, 0)
        self.assertEqual(self.run_guard("read", "src/b.py").returncode, 0)
        self.assertEqual(self.run_guard("read", "src/c.py").returncode, 2)

    def test_guard_allows_everything_while_no_task_is_in_progress(self):
        self.write_phase()
        self.assertEqual(self.run_guard("read", "src/anything.py").returncode, 0)

    def test_guard_reads_the_hook_event_from_stdin_bom_and_all(self):
        """Windows PowerShell prepends a BOM when it pipes to a native
        command. A BOM that reached json.loads would make every gate on that
        platform a silent no-op, because guard fails open."""
        self.write_phase(status="approved", ready=1, reviewed=1,
                         tasks={"T1": ([], "in_progress", ["src/a.py"])})
        target = str(self.root / "src" / "nope.py")
        payload = {"tool_name": "Read", "tool_input": {"file_path": target}}
        self.assertEqual(self.run_guard("read", payload=payload).returncode, 2)

        env = os.environ.copy()
        env["PLAN_ROOT"] = str(self.root)
        with_bom = subprocess.run(
            [sys.executable, str(PLAN), "guard", "read"],
            input=b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"),
            capture_output=True, env=env, check=False,
        )
        self.assertEqual(with_bom.returncode, 2)

    def test_guard_refuses_an_agent_written_approval(self):
        self.write_phase()
        phase = str(self.phase)
        introduces = self.run_guard("write", payload={"tool_input": {
            "file_path": phase,
            "old_string": "status: draft",
            "new_string": "status: approved"}})
        self.assertEqual(introduces.returncode, 2)
        self.assertIn("E24", introduces.stderr)

        whole_file = self.run_guard("write", payload={"tool_input": {
            "file_path": phase,
            "content": phase_text(status="approved", ready=1, reviewed=1)}})
        self.assertEqual(whole_file.returncode, 2)

    def test_guard_allows_an_edit_that_carries_an_approval_through(self):
        """Only an edit that introduces the line is an approval. An already
        approved phase edited for another reason is not."""
        self.write_phase(status="approved", ready=1, reviewed=1)
        untouched = self.run_guard("write", payload={"tool_input": {
            "file_path": str(self.phase),
            "old_string": "status: approved\nreviewed: 1",
            "new_string": "status: approved\nreviewed: 2"}})
        self.assertEqual(untouched.returncode, 0)

        source = self.run_guard("write", payload={"tool_input": {
            "file_path": str(self.root / "src" / "a.py"),
            "old_string": "x", "new_string": "status: approved"}})
        self.assertEqual(source.returncode, 0)

    def test_guard_keeps_judging_commands_out_of_the_authoring_session(self):
        self.write_phase()
        self.assertEqual(self.run_guard("stage", "/cs-plan", "--session", "A").returncode, 0)
        for judging in ("/cs-review", "/cs-approve", "/cs-close"):
            blocked = self.run_guard("stage", judging, "--session", "A")
            self.assertEqual(blocked.returncode, 2, judging)
            self.assertIn("E25", blocked.stderr)
            self.assertIn("cs-plan", blocked.stderr)
        self.assertEqual(self.run_guard("stage", "/cs-review", "--session", "B").returncode, 0)
        self.assertEqual(
            self.run_guard("stage", "/cs-review --resume", "--session", "B").returncode, 0)

    def test_guard_stage_still_bites_when_cs_plan_created_the_plan_state(self):
        """The fail-open cases must not be bought by neutering the gate.

        /cs-plan is the command that *writes* PLAN.md, so in a fresh project
        it runs with no plan state at all. Suppressing the denial by
        returning early -- before the command is recorded -- would pass every
        fail-open test above and silently disable the product's core claim on
        exactly the path it was built for. The command is recorded whatever
        the plan state; only the denial waits for state to judge against.
        """
        empty = self.root / "fresh"
        (empty / "docs" / "plans").mkdir(parents=True)
        sessions = empty / ".sessions"

        opened = self.run_guard("stage", "/cs-plan", "--session", "hot",
                                root=empty, session_dir=sessions)
        self.assertEqual(opened.returncode, 0, opened.stderr)

        # /cs-plan's own output: an index and the phase file it points at.
        (empty / "PLAN.md").write_text(
            "---\ncurrent: docs/plans/01-test.md\nworkflow-rev: 1.4.0\n---\n",
            encoding="utf-8")
        (empty / "docs" / "plans" / "01-test.md").write_text(
            phase_text(), encoding="utf-8")

        blocked = self.run_guard("stage", "/cs-review", "--session", "hot",
                                 root=empty, session_dir=sessions)
        self.assertEqual(blocked.returncode, 2,
                         "the cold-session gate stopped biting")
        self.assertIn("E25", blocked.stderr)
        self.assertIn("cs-plan", blocked.stderr)

    def test_guard_stage_closes_the_cs_recheck_alias(self):
        """/cs-recheck is a compatibility alias for /cs-review: it judges the
        same work and has to run just as cold. Listing the canonical commands
        and not the alias left the product's core claim one rename away from
        bypassable -- /cs-review returned E25 while /cs-recheck exited 0."""
        self.write_phase()
        self.assertEqual(
            self.run_guard("stage", "/cs-plan", "--session", "A").returncode, 0)

        for spelling in ("/cs-recheck", "$cs-recheck", "cs-recheck",
                         "/cs-recheck --resume"):
            blocked = self.run_guard("stage", spelling, "--session", "A")
            self.assertEqual(blocked.returncode, 2, spelling)
            self.assertIn("E25", blocked.stderr, spelling)
            # Named by what it is, not by what the user typed: cs-recheck.md
            # already tells the model to report /cs-review as the next step.
            self.assertIn("/cs-review", blocked.stderr, spelling)

    def test_guard_stage_records_the_alias_under_its_canonical_name(self):
        """Normalised going in as well as coming out, so one stage leaves one
        name in the session log however the user spelled it."""
        self.write_phase()
        self.run_guard("stage", "/cs-recheck", "--session", "R")
        log = (self.root / ".sessions" / "R.txt").read_text(encoding="utf-8").split()
        self.assertEqual(log, ["cs-review"])

    def test_the_gate_classifies_every_shipped_command(self):
        """What F4 actually was: a command shipped, and nobody decided which
        side of the gate it fell on.

        The verdict for every `cs-*` command in commands/ is asserted here, so
        adding one fails this test until somebody classifies it. Checking the
        canonical three by name could never have caught an alias for one of
        them; checking the whole shipped surface does.
        """
        expected = {
            "cs-define": 0, "cs-groundwork": 0, "cs-plan": 0, "cs-build": 0,
            "cs-revise": 0, "cs-status": 0,
            "cs-review": 2, "cs-approve": 2, "cs-close": 2, "cs-recheck": 2,
        }
        shipped = sorted(path.stem for path in (ROOT / "commands").glob("cs-*.md"))
        self.assertEqual(shipped, sorted(expected),
                         "a shipped command is unclassified by the cold-session gate")

        self.write_phase()
        self.assertEqual(
            self.run_guard("stage", "/cs-plan", "--session", "S").returncode, 0)
        for name, code in sorted(expected.items()):
            if name == "cs-plan":
                continue  # the command that opened the session
            actual = self.run_guard("stage", f"/{name}", "--session", "S")
            self.assertEqual(actual.returncode, code,
                             f"/{name} expected {code}, got {actual.returncode}")

    def test_guard_stage_ignores_prose_and_missing_session_ids(self):
        self.write_phase()
        self.run_guard("stage", "/cs-revise", "--session", "A")
        self.assertEqual(
            self.run_guard("stage", "what does /cs-review do?", "--session", "A").returncode, 0)
        self.assertEqual(
            self.run_guard("stage", payload={"prompt": "/cs-review"}).returncode, 0)

    def test_guard_lints_the_phase_file_on_write(self):
        self.write_phase()
        self.assertEqual(self.run_guard("lint", str(self.phase)).returncode, 0)

        broken = phase_text().replace(
            "  T2: {deps: [], status: pending, files: [src/b.py]}",
            "  T2 deps [] status pending")
        self.phase.write_text(broken, encoding="utf-8")
        fired = self.run_guard("lint", str(self.phase))
        self.assertEqual(fired.returncode, 2)
        self.assertIn("E01", fired.stderr)
        self.assertEqual(
            self.run_guard("lint", str(self.root / "src" / "a.py")).returncode, 0)


    def test_guard_lints_a_phase_file_the_current_pointer_has_not_reached(self):
        """The write that most needs linting is the one `current:` has not
        caught up with.

        /cs-plan writes the next phase file and only then moves the pointer,
        so linting whatever `current:` names meant the new file -- the one
        just authored, by the stage most likely to get its shape wrong -- was
        the single file the gate could not see. The hook fires on every
        Edit|Write, so the target is what decides, not the pointer.
        """
        self.write_phase()
        nxt = self.root / "docs" / "plans" / "02-next.md"
        nxt.write_text(
            phase_text().replace(
                "  T2: {deps: [], status: pending, files: [src/b.py]}",
                "  T2 deps [] status pending"),
            encoding="utf-8")

        fired = self.run_guard("lint", str(nxt))
        self.assertEqual(fired.returncode, 2,
                         "a malformed next-phase file linted clean")
        self.assertIn("E01", fired.stderr)
        self.assertIn("02-next.md", fired.stderr)

        # And the pointer is genuinely irrelevant: the same file lints clean
        # once it is well formed, still without `current:` naming it.
        nxt.write_text(phase_text(), encoding="utf-8")
        self.assertEqual(self.run_guard("lint", str(nxt)).returncode, 0)

    def test_guard_lints_the_first_phase_before_any_index_exists(self):
        """The very first /cs-plan writes a phase file into a project with no
        PLAN.md at all. Requiring an index would put that write -- the one
        with nothing to compare itself against -- back out of reach."""
        fresh = self.root / "fresh"
        (fresh / "docs" / "plans").mkdir(parents=True)
        first = fresh / "docs" / "plans" / "01-first.md"
        first.write_text(
            phase_text().replace(
                "  T2: {deps: [], status: pending, files: [src/b.py]}",
                "  T2 deps [] status pending"),
            encoding="utf-8")
        fired = self.run_guard("lint", str(first), root=fresh)
        self.assertEqual(fired.returncode, 2, fired.stderr)
        self.assertIn("E01", fired.stderr)

    def test_guard_lint_stays_silent_on_docs_plans_files_that_are_not_ours(self):
        """Widening past the `current:` pointer must not widen past
        coldsession. A repository that keeps unrelated markdown under
        docs/plans/ gets nothing, because the gate matches on the phase
        marker in the file rather than on its location."""
        strangers = {
            "notes.md": "# just some notes\n\nnothing structured here.\n",
            "rfc.md": "---\ntitle: an rfc\nstatus: draft\n---\n\n# body\n",
            "01-test.log.md": "# handoff log\n\n- something happened\n",
        }
        for name, text in strangers.items():
            path = self.root / "docs" / "plans" / name
            path.write_text(text, encoding="utf-8")
            result = self.run_guard("lint", str(path))
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")
            self.assertEqual(result.stderr, "", name)

    def test_shipped_phase_template_lints_clean(self):
        """CONTRIBUTING's rule, checked instead of remembered: the template a
        phase is written from has to pass the linter that judges it, so a new
        prose section can never quietly break a fresh plan."""
        self.phase.write_text(
            (ROOT / "templates" / "phase.md").read_text(encoding="utf-8"),
            encoding="utf-8")
        result = self.run_plan("lint")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)


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

    def test_every_hook_ships_for_both_shells(self):
        """Windows parity, checked rather than remembered: a gate that only
        has a .sh is a gate that silently does not exist on the PowerShell
        install path."""
        hooks = ROOT / "hooks"
        for kind in ("read", "write", "lint", "stage"):
            posix = hooks / f"cs-guard-{kind}.sh"
            windows = hooks / f"cs-guard-{kind}.cmd"
            self.assertTrue(posix.exists(), posix)
            self.assertTrue(windows.exists(), windows)
            for path in (posix, windows):
                raw = path.read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), f"{path} has a BOM")
                raw.decode("ascii")
                self.assertIn(f"guard {kind}".encode(), raw)
            self.assertNotIn(b"\r", posix.read_bytes(), f"{posix} must be LF")
            self.assertIn(b"\r\n", windows.read_bytes(), f"{windows} must be CRLF")

    def test_the_codex_adapter_keeps_the_rule_claude_now_enforces(self):
        """Enforcement asymmetry, stated once and asserted here: the bounded
        read rule left cs-build.md when the hook took it over, so the Codex
        adapter -- which has no hooks -- has to carry it in prose."""
        skill = (ROOT / "skills" / "cs-build" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Read exactly the files the brief lists", skill)
        self.assertIn("Nothing else.", skill)

    def test_policy_skills_are_host_owned_and_surface_neutral(self):
        """The policy layer is a convention, not shipped content, so the only
        thing holding it together is prose in two command files. Those files
        are copied to Codex with the runtime path patched and nothing else,
        so naming only the Claude skills directory would silently mislead
        every Codex install."""
        plan_cmd = (ROOT / "commands" / "cs-plan.md").read_text(encoding="utf-8")
        review_cmd = (ROOT / "commands" / "cs-review.md").read_text(encoding="utf-8")
        for name, text in (("cs-plan", plan_cmd), ("cs-review", review_cmd)):
            self.assertIn("`policy-*`", text, name)
            self.assertIn(".claude/skills/", text, name)
            self.assertIn(".agents/skills/", text, name)

        # Plan applies them and records the judgement; absence is silence.
        self.assertIn("## Apply project policy", plan_cmd)
        self.assertIn("`None.` and invent", plan_cmd)
        self.assertIn("`## Policy`", plan_cmd)

        # Review re-derives the list rather than trusting what Plan wrote,
        # and files misses in the new category.
        self.assertIn("Do not take the phase's `## Policy` section as the list",
                      review_cmd)
        self.assertIn("`Policy`", review_cmd)
        self.assertIn("absence is never a finding", review_cmd)

        # The template carries the section a fresh phase writes into.
        template = (ROOT / "templates" / "phase.md").read_text(encoding="utf-8")
        self.assertIn("## Policy", template)
        self.assertLess(template.index("## Policy"), template.index("## Findings"))

        # No installer may manage a host-owned skill.
        for installer in ("install.sh", "install.ps1"):
            self.assertNotIn(
                "policy-", (ROOT / installer).read_text(encoding="utf-8"), installer)

    def test_installers_agree_on_the_hook_surface(self):
        posix = (ROOT / "install.sh").read_text(encoding="utf-8")
        powershell = (ROOT / "install.ps1").read_text(encoding="utf-8")
        for kind in ("read", "write", "lint", "stage"):
            self.assertIn(f"cs-guard-{kind}.sh", posix)
            self.assertIn(f"cs-guard-{kind}.cmd", powershell)
        # Both must keep recognising the three-key default written before
        # hooks existed, or an upgrading user is warned about a file they
        # never touched.
        self.assertIn('{"model", "env", "permissions"}', posix)
        self.assertIn('@("model", "env", "permissions")', powershell)


class InstalledHookTest(unittest.TestCase):
    """The hooks as a hook host actually runs them.

    Every other installer test in this file asserts on installer *source
    text*, which is why a generated hook command that no shell can launch
    survived a green suite: nothing ever ran one. These install for real and
    execute what landed in `.claude/settings.json`.

    The project directory contains a space on purpose. A command the shell
    splits on that space exits 127, and a non-zero exit from a `PreToolUse`
    hook blocks the tool -- so an unquoted path does not merely miss a gate,
    it fails CLOSED on every file operation in the project, which is the one
    outcome the whole design is built to avoid.
    """

    def spaced_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dest = Path(tmp.name) / "scratch dir" / "proj"
        dest.mkdir(parents=True)
        return dest

    def install(self, flavour, dest, agent="both"):
        if flavour == "sh":
            argv = [BASH, str(ROOT / "install.sh"),
                    str(dest).replace("\\", "/"), "--agent", agent]
        else:
            argv = [POWERSHELL, "-NoProfile", "-NonInteractive", "-File",
                    str(ROOT / "install.ps1"), "-Target", str(dest),
                    "-Agent", agent]
        result = subprocess.run(argv, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0,
                         f"{flavour} installer failed:\n{result.stdout}{result.stderr}")
        return result

    def hook_commands(self, dest):
        settings = json.loads(
            (dest / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))
        return [(event, spec["command"])
                for event, entries in settings["hooks"].items()
                for entry in entries
                for spec in entry["hooks"]]

    def run_hook_command(self, command, dest, payload=None):
        """Hand the whole command string to a shell, the way a hook host does.

        Deliberately not an argv list: Python would re-quote each element and
        paper over exactly the missing quotes this exercises. The shell has to
        do the word splitting for the test to mean anything.
        """
        if command.rstrip('"').endswith(".cmd"):
            expanded = command.replace("$CLAUDE_PROJECT_DIR", str(dest))
            argv, shell = expanded, True
        else:
            expanded = command.replace("$CLAUDE_PROJECT_DIR",
                                       str(dest).replace("\\", "/"))
            argv, shell = [SH, "-c", expanded], False
        env = os.environ.copy()
        # Keep session state inside the fixture: `plan guard stage` otherwise
        # writes to the shared system temp directory, where one run's session
        # log would decide the next run's verdict.
        env["PLAN_SESSION_DIR"] = str(dest / ".sessions")
        result = subprocess.run(
            argv, shell=shell, input=json.dumps(payload or {}), text=True,
            capture_output=True, cwd=str(dest), env=env, check=False)
        return expanded, result

    def assert_hooks_launch_from_a_spaced_path(self, flavour):
        dest = self.spaced_project()
        self.install(flavour, dest)
        commands = self.hook_commands(dest)
        self.assertEqual(len(commands), 4, commands)

        for event, command in commands:
            with self.subTest(flavour=flavour, event=event):
                # The whole executable path as one quoted token. Claude Code
                # substitutes $CLAUDE_PROJECT_DIR and hands the result to a
                # shell; nothing downstream can re-quote it.
                self.assertEqual(
                    command.count('"'), 2,
                    f"{command!r} does not quote the executable path")
                self.assertTrue(command.startswith('"') and command.endswith('"'),
                                f"{command!r} is not a single quoted token")

                expanded, ran = self.run_hook_command(command, dest)
                self.assertNotEqual(
                    ran.returncode, 127,
                    f"the shell could not launch {expanded!r}: the gate fails closed")
                # No PLAN.md anywhere in this project, so every gate must also
                # fail open here -- the real hook path, not the wrapper.
                self.assertEqual(ran.returncode, 0,
                                 f"{expanded!r} exited {ran.returncode}\n{ran.stderr}")
                self.assertEqual(ran.stderr, "", f"{expanded!r} was not silent")

    @unittest.skipUnless(BASH and SH, "needs a POSIX shell")
    def test_sh_installed_hooks_launch_from_a_path_with_a_space(self):
        self.assert_hooks_launch_from_a_spaced_path("sh")

    @unittest.skipUnless(POWERSHELL and os.name == "nt", "needs Windows PowerShell")
    def test_powershell_installed_hooks_launch_from_a_path_with_a_space(self):
        self.assert_hooks_launch_from_a_spaced_path("ps1")

    def assert_stage_gate_fails_open_without_a_plan(self, flavour):
        """F2 through the real hook path.

        An audit can only reach `plan guard` and the wrapper; neither shows
        what the command registered in settings.json actually does to a
        session. This drives the installed UserPromptSubmit hook with the
        event JSON Claude Code sends, in a project that has no PLAN.md --
        which is every repository that never adopted coldsession.
        """
        dest = self.spaced_project()
        self.install(flavour, dest)
        stage = dict(self.hook_commands(dest))["UserPromptSubmit"]
        for prompt in ("/cs-plan", "/cs-revise", "/cs-review",
                       "/cs-approve", "/cs-close"):
            with self.subTest(flavour=flavour, prompt=prompt):
                expanded, ran = self.run_hook_command(
                    stage, dest, {"session_id": "cold-open", "prompt": prompt})
                self.assertEqual(
                    ran.returncode, 0,
                    f"{prompt} denied with no plan state\n{ran.stderr}")
                self.assertEqual(ran.stderr, "", f"{prompt}: {ran.stderr!r}")

    @unittest.skipUnless(BASH and SH, "needs a POSIX shell")
    def test_sh_installed_stage_hook_fails_open_without_a_plan(self):
        self.assert_stage_gate_fails_open_without_a_plan("sh")

    @unittest.skipUnless(POWERSHELL and os.name == "nt", "needs Windows PowerShell")
    def test_powershell_installed_stage_hook_fails_open_without_a_plan(self):
        self.assert_stage_gate_fails_open_without_a_plan("ps1")

    def test_at_least_one_installer_is_exercisable_here(self):
        """A platform where neither installer can run would skip every test
        above and still report green. Say so instead."""
        self.assertTrue(bool(BASH and SH) or bool(POWERSHELL and os.name == "nt"),
                        "no installer flavour is runnable on this platform")


if __name__ == "__main__":
    unittest.main()
