---
description: Create the initial or next detailed phase from durable state
argument-hint: [phase guidance] [--resume]
---

Create exactly one implementation phase. `$ARGUMENTS` is supplemental phase
guidance, never a replacement for durable project state.

## Select the source without drifting scope

Check whether `PLAN.md` exists before opening `OBJECTIVE.md`.

### No PLAN.md

Require root `OBJECTIVE.md` with `status: ready`; otherwise stop and tell me to
run `/cs-define`. Read it once as the authoritative product scope. Additional
arguments may clarify it but may not silently contradict it; a conflict must
be resolved with `/cs-define --revise` before planning.

If `OBJECTIVE.md` says `active: plan`, require `--resume`; another active value
stops. Otherwise set `active: plan` before substantive planning. Copy its
`objective-rev:` into the new PLAN.md.

### PLAN.md exists

Do not open, search, quote, or otherwise read `OBJECTIVE.md`, even on
`--resume`. Product scope has already been reduced to the phase index.

- If the current phase is not closed, stop before source inspection, run
  `.claude/bin/plan recommend`, and print it. Never rewrite an active phase.
- If the current phase is closed and has `active: plan`, require `--resume`.
- Otherwise set `active: plan` on that closed phase before substantive work.
- Plan the first unticked phase, or the phase named by `current:` when no
  later line exists. Read its PLAN.md line, the closed phase and only the last
  log entry, AGENTS.md, and docs/architecture.md if present. Use targeted
  repository search and read only files needed to make task paths exact.

A one-line phase is an intention, not a specification. Ask all material
questions before writing, as one numbered round: every question asked together,
each with its recommended answer, then stop and wait. Find facts yourself with a
search subagent rather than asking me for anything discoverable.

Normally one round, at most two. Phase scope is not product scope and Plan is
not a second Define. Needing a third round means the phase is too large; split
it, exactly as a third review round does.

## Apply project policy

Policy is the project's, not this workflow's: brand, security, compliance, UX,
data handling. It lives in skills the project owns, named `policy-*`, in the
skills directory the agent already reads — `.claude/skills/` under Claude
Code, `.agents/skills/` under Codex. The `cs-*` skills are this workflow's own
invocation adapters and carry no project policy; the prefix is what keeps the
two apart.

List that directory and read only each `policy-*` skill's frontmatter
`description`. Open in full just the ones this phase can actually violate —
payment copy policy is not input to a migration phase. If the directory holds
no `policy-*` skill there is no policy layer here: write `None.` and invent
none.

An applicable policy constrains the phase the way any durable constraint does.
It may add acceptance criteria to a task, add a task, or put a file in a
`files` list the goal alone would not have needed — and when it does, that
file goes in `files` now rather than when Build discovers it missing. It never
widens product scope. A policy that contradicts the phase is an open question,
not a silent choice.

Record every `policy-*` skill you considered in `## Policy`, one per line,
three fields, no pipes inside the prose:

  policy-a11y | T2, T4 | contrast and focus order on the new list view
  policy-billing | - | not applicable; this phase touches no pricing surface

Review lists the same skills itself. The section is there so it can check the
judgement rather than repeat it.

## Plan quality

Break the work into dependency-ordered phases and detail only the current one.
Every phase must end in a runnable state. Later phase lines stay provisional.

Use `templates/PLAN.md` and `templates/phase.md`. PLAN.md remains only the
`current:` pointer and one-line phase checklist. The phase file is
`docs/plans/(NN)-(slug).md`.

The task graph uses exactly:

  T2: {deps: [T1], status: pending, files: [src/sync/queue.ts]}

- At most eight tasks; split the phase rather than add a ninth.
- Dependencies are real prerequisites in this phase and form an acyclic graph.
- `files` is the complete, minimal set the task may read or write, including
  tests, configuration, generated definitions, and new files. Missing paths
  stall Build; broad paths waste context.
- Keep concurrently runnable tasks from sharing files where practical.

Size every task at the lowest rung that holds, and stop there:

1. No task at all, because an existing capability already covers it.
2. A configuration or flag change.
3. An extension of an existing file or function.
4. A new file.
5. A new abstraction or module.

A task sized one rung too high inflates `files`, and `files` is the contract a
Build session is bounded to. Over-scope here is not untidiness; it is context
the phase spends and does not get back.

Each matching `## T(n)` contains Goal, concrete Deliverables, observable
Acceptance Criteria, and `Verify:` with an exact runnable command and exact
passing output or exit status. For a genuinely visual-only result, name the
screen, action, and visible result. Never use "manually confirm it works".

Resolve blocking questions before writing. Record confirmed non-blocking
assumptions, `## Open questions` as `None.`, explicit out-of-scope items, and
`## Policy` as above.
Leave Findings and Changelog empty and omit `reviewed:`, `ready:`, and active
stage metadata from a new phase.

## Atomic handoff

Write and lint the new phase before moving `current:`. At a boundary, remove
`active: plan` from the closed phase in the same final edit that creates the
new phase and moves the pointer. On initial planning, remove `active: plan`
from OBJECTIVE.md only after both PLAN.md and the phase file exist.

Then:

1. `.claude/bin/plan lint` — fix every error and warning attributable to the plan.
2. `.claude/bin/plan recommend` — print it.
3. Stop and tell me to run `/cs-review` in a new session.
