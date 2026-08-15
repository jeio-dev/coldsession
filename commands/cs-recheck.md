---
description: Scoped re-review against the changelog, round 2 and after
---

Run `.claude/bin/plan lint`, `.claude/bin/plan status`, and
`.claude/bin/plan findings`. Those name your scope. Then read the phase file's
`## Changelog` and frontmatter, and only the tasks the changelog names. Do not
re-review the phase end to end — /cs-review already did, and the rev the
changelog stamps tells you what has changed since.

You did not write these resolutions.

For each finding the changelog claims `resolved` or `accepted`, decide:
actually resolved, partially resolved, or not resolved. Quote the plan line
that settles it. A note that does not name a task ID or plan line is not
evidence; that finding is not resolved.

Reopen anything that does not hold up:

  .claude/bin/plan resolve F2 open "worker.ts still missing from T4 files"

Then check only three things beyond that:
- Did any resolution create a new dependency, ordering, or scope problem?
  New findings continue the existing numbering — append them to `## Findings`
  in the same seven-field shape /cs-review uses, status `open`.
- Did any resolution change what a task touches without updating its `files`
  list?
- Did any Medium marked `accepted` get a real reason, or a restatement of the
  finding?

## Finishing

1. `.claude/bin/plan reviewed` — records that this rev has been checked.
2. `.claude/bin/plan lint`, then `.claude/bin/plan recommend` and print it.
   Open findings send you back to /cs-revise; a clean pass sends you to /cs-approve.
   At rev 3 with a Critical still open it will tell you to split the phase
   instead — that is the stop condition, and it is the right answer.
3. End with one line: what this pass did NOT look at.
