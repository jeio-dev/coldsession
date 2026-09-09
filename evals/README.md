# Prompt evals

`tests/test_plan.py` exercises `bin/plan`, the deterministic runtime. It says
nothing about the prompts in `commands/`: a reworded `cs-review.md` that
quietly stopped writing findings would pass every existing test. These
fixtures close that gap by running the real `cs-*` command headlessly
against a fixture repo in a known state, then grading the result on
machine-readable state (`plan lint`, `plan status`, `plan findings`, the
`reviewed:`/`ready:`/`rev:` frontmatter) — never on prose, per the same
philosophy the rest of the project already uses.

Claude surface only, for now: it runs the fixture through `claude -p`. A
Codex-surface runner (`codex exec` or equivalent) is a natural follow-up,
not built here.

## Running

```
python evals/run.py                          # every fixture
python evals/run.py review-writes-findings    # one fixture
python evals/run.py --keep some-fixture       # keep the temp project dir
```

Needs the `claude` CLI on `PATH` and authenticated. Each run creates a throw-
away project directory (via the real installer, so it matches what a user
gets), invokes the fixture's `prompt.txt` against it with
`--permission-mode bypassPermissions` — safe because the directory is a
temp copy this harness owns, never the working repo — and grades the result.
`--max-budget-usd` (default $2.00 per fixture) caps API spend on a run that
goes sideways.

## Why this isn't wired into CI

The plan this package implements calls for triggering on any change to
`commands/`, `skills/`, `templates/`, or `bin/plan`, plus a schedule — the
playbook's Stage 4 recipe. Doing that for real means a GitHub Actions job
that calls a live model on every matching push, which needs an API key
committed to the repo's secrets and a standing decision about who pays for
it. That's a real decision, and it has been made: declined, deliberately.
This harness is a manual pre-PR tool by design — runnable by hand, fully
tested without spending a token via `tests/test_evals.py`. CI wiring stays
possible (it would add one workflow file on top of working infrastructure)
but it is not planned.

## Fixtures

Each fixture is `evals/fixtures/<name>/`:

- `project/` — the files a temp project starts with (`PLAN.md`,
  `docs/plans/*.md`, `AGENTS.md`, `OBJECTIVE.md` when relevant).
- `prompt.txt` — the one line passed to `claude -p`.
- `expect.py` — a `grade(ctx) -> list[str]` function. An empty list means the
  fixture passed; each string in a non-empty list is one failure reason.
  `ctx` (see `evals/lib.py`) exposes `plan(*args)` to shell out to the
  installed `plan` binary, `text(relpath)` / `exists(relpath)` to read the
  resulting project files directly, and `tool_inputs_mentioning(needle)` to
  check the tool-call trace for contracts machine state alone can't prove
  (like "never reads OBJECTIVE.md once PLAN.md exists").

Shipped fixtures, the highest-value three named in the plan:

- `review-writes-findings` — an unreviewed phase with a real, deliberate
  ordering gap (a task needs a file only an earlier task produces, but has
  neither the dependency edge nor the `files` entry). A compliant
  `/cs-review` must catch it and finish the review stage.
- `approve-refuses-to-set-status` — a clean, reviewed, finding-free phase.
  `/cs-approve` must record `ready: <rev>` without ever setting
  `status: approved` itself; only the human edit may.
- `plan-does-not-reread-objective` — `PLAN.md` already exists and points at
  a closed phase with an unticked next phase line. `/cs-plan` must write the
  next phase without ever reading root `OBJECTIVE.md` again.

These three cover the highest-value contracts; the harness accepts new
fixtures the same way if another contract needs one.
