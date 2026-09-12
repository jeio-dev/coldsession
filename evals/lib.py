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
import time
import threading
import re
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
            env=isolated_env(self.tmp),
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
    result = subprocess.run(cmd, text=True, capture_output=True, check=False, env=isolated_env(tmp))
    if result.returncode != 0:
        raise FixtureError(
            f"install failed for fixture {name}:\n{result.stdout}{result.stderr}"
        )
    preview = json.loads(result.stdout)['preview']
    result = subprocess.run(cmd + (['-Apply', preview] if os.name == 'nt' else ['--apply', preview]),
                            text=True, capture_output=True, check=False, env=isolated_env(tmp))
    if result.returncode:
        raise FixtureError('install apply failed: ' + result.stderr)

    src = FIXTURES / name / "project"
    if not src.exists():
        raise FixtureError(f"fixture {name} has no project/ directory")
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        dest = tmp / item.relative_to(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, dest)


def isolated_env(tmp):
    """Allowlist process essentials/auth; never inherit plugins or session identity."""
    allowed = {'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP',
               'LANG', 'LC_ALL', 'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
               'ANTHROPIC_API_KEY', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    config = Path(tmp) / '.eval-config'
    config.mkdir(exist_ok=True)
    env['CLAUDE_CONFIG_DIR'] = str(config)
    return env


def redact(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if re.search(r'(?i)(?:^|_)(?:token|secret|password|api.?key|authorization)$', k)
                and not isinstance(v, (int, float)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)\b(token|secret|password|api[_-]?key|authorization)\s*[:=]\s*[^\r\n]+', r'\1=[REDACTED]', value)
        return re.sub(r'\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]{15,}|AKIA[A-Z0-9]{16})\b', '[REDACTED]', value)
    return value


def run_claude(tmp, prompt, max_budget_usd=DEFAULT_MAX_BUDGET_USD, timeout=600):
    """Bounded isolated invocation. Native permissions remain active; failures count."""
    if float(max_budget_usd) <= 0:
        raise FixtureError('budget must be positive')
    cmd = ["claude", "-p", prompt,
           "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers":{}}',
           "--max-budget-usd", str(max_budget_usd)]
    events = []
    output, retained, truncated = [], [0], [False]
    started = time.monotonic()
    try:
        process = subprocess.Popen(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=isolated_env(tmp), start_new_session=os.name != 'nt')
    except OSError as exc:
        raise FixtureError(str(exc)) from exc
    def drain():
        while True:
            raw = process.stdout.readline(65537)
            if not raw:
                break
            if len(raw) > 65536:
                truncated[0] = True
                while raw and not raw.endswith(b'\n'):
                    raw = process.stdout.readline(65537)
                continue
            text = raw.decode('utf-8', 'replace')
            try:
                event = redact(json.loads(text))
            except ValueError:
                if sum(map(len, output)) < 16384:
                    output.append(redact(text)[:4096])
                continue
            if retained[0] + len(raw) <= 4 * 1024 * 1024 or event.get('type') == 'result':
                events.append(event)
                retained[0] += len(raw)
            else:
                truncated[0] = True
    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    reader.join(timeout=2)
    if not reader.is_alive():
        process.stdout.close()
    result = subprocess.CompletedProcess(cmd, process.returncode, ''.join(output)[:16384], '')
    result.elapsed_seconds = time.monotonic() - started
    result.truncated = truncated[0] or reader.is_alive()
    result.timed_out = timed_out
    return events, result
