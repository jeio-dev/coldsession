---
description: Scoped re-review against the changelog, round 2 and after
---

Run `.claude/bin/plan lint`. Then read the phase file's changelog and
frontmatter, and only the tasks the changelog names. Do not re-review the
phase end to end.

For each finding ID the changelog claims resolved, decide: actually resolved,
partially resolved, or not resolved. Quote the plan line that settles it.

Then check only three things beyond that:
- Did any resolution create a new dependency, ordering, or scope problem?
  New findings continue the existing numbering.
- Did any resolution change what a task touches without updating its `files`
  list?
- Did any Medium marked "not adopted" get a real reason, or a restatement of
  the finding?

End with one line: what this pass did NOT look at.
