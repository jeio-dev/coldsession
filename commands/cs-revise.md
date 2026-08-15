---
description: Resolve findings in place and write the changelog
---

Run `.claude/bin/plan findings --open`. Those are what you resolve — not a
list you remember from earlier in the session, and not a list I paste in. If
it prints nothing open, stop and tell me there is nothing to revise.

Then `.claude/bin/plan bump`, once, before you edit anything. Every changelog
line you write from here is stamped with the new rev.

Revise the phase file in place. Do not create a second file. If a finding
changes the phase ordering, update PLAN.md as well.

Resolve every Critical and High finding.
For each Medium finding, either implement the recommendation or state why it
was not adopted.
Low findings may be addressed at your discretion.

Preserve task IDs where possible. If tasks are added, removed, or split,
update the frontmatter graph in the same edit — the graph and the `## T(n)`
sections must stay in sync, and `.claude/bin/plan lint` will fail if they
drift.

## Closing each finding

After the edit that fixes it, close the finding with the tool rather than by
hand-editing its line:

  .claude/bin/plan resolve F1 resolved "T3 now depends on T2"
  .claude/bin/plan resolve F3 accepted "types.ts kept: T1 exports rows, not wire types"

`resolved` means the plan changed. `accepted` means it did not and here is
why. The note must name the task ID or plan line that now carries the fix —
"done" or "fixed" tells /cs-recheck nothing, and /cs-approve will fail that line.
`plan resolve` writes the changelog entry for you; do not also write one by
hand.

Leave a finding `open` if you could not resolve it, and say which and why.

## Finishing

1. `.claude/bin/plan lint` — fix anything it reports.
2. `.claude/bin/plan recommend` and print it. It will send you to /cs-recheck,
   which reads the changelog you just wrote.
3. Stop, and exit the session. /cs-recheck must not run here: it would be
   grading its own work.
