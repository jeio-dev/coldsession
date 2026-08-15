---
description: Resolve findings in one guarded revision and write the changelog
argument-hint: [--resume]
---

First run `.claude/bin/plan begin revise $ARGUMENTS` and inspect only its
output. If it refuses, print that output and stop. A matching interrupted pass
continues only with `--resume`.

Run `.claude/bin/plan bump`. It increments once for a new Revise pass and is a
safe no-op on resume; never hand-edit `rev:`. Then run `plan findings --open`.

Revise the current phase in place. Do not create a replacement file. Update
PLAN.md only when a finding changes phase ordering.

- Resolve every Critical and High.
- Resolve each Medium or explicitly accept it with a concrete reason.
- Low findings are discretionary.
- Preserve task IDs where possible and keep graph entries and task sections in
  sync when tasks change.

After the edit, close each addressed finding through the runtime:

  .claude/bin/plan resolve F1 resolved "T3 now depends on T2"
  .claude/bin/plan resolve F3 accepted "T2 exports rows; the types line stays"

`resolved` means the plan changed. `accepted` means it did not. The note must
name the task or plan line carrying the resolution; never write "done" or
"fixed". Leave genuinely unresolved findings open and explain why.

Finish with:

1. `.claude/bin/plan lint` — fix errors introduced by the revision.
2. `.claude/bin/plan finish revise` — clear the active marker only after the
   revision and changelog are durable.
3. `.claude/bin/plan recommend` and print it. An unreviewed revision always
   returns to `/cs-review`, even when a finding remains open.
4. Stop and exit. Review must run in a new session.
