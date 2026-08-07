---
description: Resolve findings in place and write the changelog
---

Revise the phase file in place. Bump `rev` in its frontmatter. Do not create a
second file. If a finding changes the phase ordering, update PLAN.md as well.

Resolve every Critical and High finding.
For each Medium finding, either implement the recommendation or state why it
was not adopted.
Low findings may be addressed at your discretion.

Preserve task IDs where possible. If tasks are added, removed, or split,
update the frontmatter graph in the same edit — the graph and the `## T(n)`
sections must stay in sync, and `.claude/bin/plan lint` will fail if they
drift. Run it when you are done.

Include a changelog mapping each finding ID to the resolution taken, and for
each one, the task ID or plan line that now carries the fix.
