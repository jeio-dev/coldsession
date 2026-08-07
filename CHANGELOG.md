# Changelog

Format version and release version are the same number. A phase file records
the version it was planned under as `workflow-rev`, and `plan lint` refuses a
file whose major version differs from the tool's.

## [1.0.1] — 2026-08-07

Audit release. No command prompt content changed.

- Reviewed all ten `commands/*.md` files against Anthropic's July 2026
  guidance on Claude 5-generation context engineering (rigid rules replaced
  with judgment-based instructions where the rule was compensating for
  weaker model judgment). Found nothing to change: this tool has no
  docstring/comment-style rules, and its hard "Never/Do not" rules are either
  mechanical parser requirements, self-grading/corner-cutting guardrails, or
  context-budget discipline — none are model-capability crutches.
- `bin/plan` and `install.sh` marked executable (file mode only, no content
  change).

## [1.0.0] — 2026-08-07

First release.

### The loop
- Ten commands: `/define`, `/groundwork`, `/plan`, `/review`, `/revise`,
  `/recheck`, `/approve`, `/build`, `/close`, `/status`.
- Every step that judges the previous one runs in a new session.
- `/approve` produces evidence and no verdict; a human sets
  `status: approved`.
- Stop condition at round three: split the phase rather than revise again.

### Task graph
- Machine-readable `tasks:` frontmatter carrying `deps`, `status`, and
  `files` per task, with the prose in the body and no duplication between
  them.
- `plan lint` catches cycles, unknown or forward dependencies, tasks done
  ahead of their dependencies, empty file lists, missing `Verify:` lines, and
  graph/body drift. `/review` and `/approve` both run it.
- `plan next --parallel` groups runnable tasks by file overlap.
- `plan done` refuses a task whose dependency is unfinished.

### Context
- `plan brief` computes a bounded read list: `AGENTS.md`, the phase file,
  direct dependencies' files, then the task's own. Build reads that and
  nothing else, in that order, so the cache prefix stays stable across the
  phase.
- An unlisted file stops the session instead of widening it.
- Search delegated to a subagent returning `file:line`.
- Handoffs appended to `docs/plans/NN-slug.log.md`, ten lines maximum.

### Build
- A task is done only when its `Verify` command has run and its output is
  shown.
- Explicit rule for when two tasks may share a session.
- Correction harvesting moved to `/close`, where a one-task-per-session
  workflow can actually count repeats.
