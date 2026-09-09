"""Shared harness for prompt evals: fixture setup, live invocation, grading.

Fixture *state* is graded exactly the way tests/test_plan.py grades runtime
state -- shelling out to the installed `plan` binary and asserting on its
output, because that is the one parser this project trusts. The one addition
here is `tool_inputs_mentioning`, for the handful of contracts ("do not read
OBJECTIVE.md once PLAN.md exists") that machine state alone cannot prove --
those need the tool-call trace instead of the file the trace produced.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

DEFAULT_MAX_BUDGET_USD = "2.00"


class FixtureError(Exception):
    pass


def _content_blocks(event):
    message = event.get("message") if isinstance(event, dict) else None
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return content if isinstance(content, list) else []


@dataclass
class EvalContext:
    """What an expect.py's grade(ctx) function gets to inspect."""

    tmp: Path
    events: list = field(default_factory=list)

    def plan(self, *args, ok=False):
        """Run the fixture's installed `plan` binary, cwd at the project root."""
        result = subprocess.run(
            [sys.executable, str(self.tmp / ".claude" / "bin" / "plan"), *args],
            cwd=self.tmp, text=True, capture_output=True, check=False,
        )
        if ok and result.returncode != 0:
            raise AssertionError(
                f"plan {' '.join(args)} failed:\n{result.stdout}{result.stderr}"
            )
        return result

    def text(self, relpath):
        return (self.tmp / relpath).read_text(encoding="utf-8-sig")

    def exists(self, relpath):
        return (self.tmp / relpath).exists()

    def tool_inputs_mentioning(self, needle):
        """tool_use blocks whose JSON input contains `needle` (case-insensitive).

        Grades a "must not read X" contract from the trace: a file that was
        never opened leaves no trace in the file state a grader could check
        instead.
        """
        needle = needle.lower()
        hits = []
        for event in self.events:
            for block in _content_blocks(event):
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                blob = json.dumps(block.get("input", {})).lower()
                if needle in blob:
                    hits.append(block)
        return hits


def list_fixtures():
    if not FIXTURES.exists():
        return []
    return sorted(p.name for p in FIXTURES.iterdir() if (p / "expect.py").exists())


def load_expect(name):
    path = FIXTURES / name / "expect.py"
    if not path.exists():
        raise FixtureError(f"no such fixture: {name} ({path} does not exist)")
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"eval_expect_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "grade"):
        raise FixtureError(f"{name}/expect.py has no grade(ctx) function")
    return module.grade


def setup_project(name, tmp):
    """Install coldsession into `tmp`, then overlay the fixture's project/ files.

    Goes through the real installer rather than hand-copying `commands/` and
    `bin/plan`, so a fixture run also mirrors what a real project gets --
    same settings.json, same runtime layout CONTRIBUTING.md's own pre-PR
    check produces.
    """
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-File",
               str(ROOT / "install.ps1"), "-Target", str(tmp), "-Agent", "claude"]
    else:
        cmd = [str(ROOT / "install.sh"), str(tmp), "--agent", "claude"]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise FixtureError(
            f"install failed for fixture {name}:\n{result.stdout}{result.stderr}"
        )

    src = FIXTURES / name / "project"
    if not src.exists():
        raise FixtureError(f"fixture {name} has no project/ directory")
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        dest = tmp / item.relative_to(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, dest)


def run_claude(tmp, prompt, max_budget_usd=DEFAULT_MAX_BUDGET_USD):
    """Invoke the real cs-* command headlessly; return (events, CompletedProcess).

    Runs with --permission-mode bypassPermissions: safe here because `tmp` is
    a throwaway directory this harness created for one fixture, never the
    working repo.
    """
    cmd = ["claude", "-p", prompt,
           "--output-format", "stream-json", "--verbose",
           "--permission-mode", "bypassPermissions",
           "--max-budget-usd", str(max_budget_usd)]
    result = subprocess.run(cmd, cwd=tmp, text=True, capture_output=True, check=False)
    events = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events, result
