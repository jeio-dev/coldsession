---
description: Turn the objective brief into a phased plan on disk
argument-hint: [objective, or blank to use the brief from this session]
---

Create a complete implementation plan for the following objective:

$ARGUMENTS

If the line above is blank, work out what you are planning against, in this
order:

1. An objective brief produced earlier in this session: use it.
2. No brief, but PLAN.md exists: this is a phase boundary, and the objective
   is the phase `current:` names, or the first unticked phase if `current:`
   names a closed one. Read its line in PLAN.md, the closed phase file and
   its `.log.md` for what carries forward, AGENTS.md, and
   docs/architecture.md if it exists. Nothing else. The product scope is
   settled; do not re-derive it, and do not run /cs-define.
3. Neither: stop and tell me to run /cs-define first.

Coming in at a boundary you will have real questions — a one-line phase name
is an intention, not a specification. Ask them, per `## Also include` below,
before you write the file.

Break the work into logical phases, and phases into numbered tasks
(T1, T2, T3, ...).

## Files

PLAN.md is the index: a `current:` pointer and a checklist of phases in
dependency order, one line each, linking to their phase files. Create it from
templates/PLAN.md if absent; otherwise add or correct phases and set
`current:` to this one. Never copy task detail into PLAN.md.

Setting `current:` is yours alone. /cs-close leaves it on the phase it closed,
so at a boundary it still names the previous phase until you move it. Move it
in the same edit that writes the new phase file, never before.

Write the current phase to docs/plans/(NN)-(slug).md using
templates/phase.md. Detail only the current phase at task level. Phases
beyond it are provisional: reorder, split, merge, or drop them freely at each
boundary.

## Task graph

The phase file's frontmatter carries a machine-readable graph. One line per
task, exactly this shape, or the tooling cannot read it:

  T2: {deps: [T1], status: pending, files: [src/sync/queue.ts]}

- `deps` are task IDs in this phase only. Acyclic, and prefer depending
  backwards so IDs read in execution order.
- `files` is the complete set this task may open or write. A build session is
  bounded to this list plus its dependencies' files, so a missing entry stalls
  the build and an over-broad one wastes context. This is the single most
  important field you write.
- `status` starts as pending.

## Task body

One `## T(n)` section per task, matching the graph exactly:
- Goal
- Deliverables
- Acceptance Criteria
- Verify: the exact command I run and the exact output that means it passed.
  If the only check is visual, name the screen and what I should see. Never
  write "manually confirm it works".

## Size

Cap a phase at eight tasks. A ninth is a signal the phase should split: every
later session pays to read this file, so it stays small. Each phase must end
in a state I can run.

## Also include

- Assumptions you are proceeding on without confirming
- Open questions that need my input before this plan is final
- Out of scope items

Leave the `## Findings` and `## Changelog` sections in place and empty.
/cs-review writes the first, /cs-revise writes the second, and they are how those
sessions hand work to each other. Do not add a `reviewed:` field — the phase
has not been reviewed, and the tooling reads its absence.

Ask me the open questions directly rather than guessing. Do not write code.

## Finishing

1. `.claude/bin/plan lint` — fix anything it reports.
2. `.claude/bin/plan recommend` and print it. It will send you to /cs-review.
3. Stop, and tell me to run /cs-review in a NEW session. /cs-review typed here
   reviews its own work and will agree with itself.
