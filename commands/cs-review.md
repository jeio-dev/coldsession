---
description: State-aware independent review of the current phase
---

Run `.claude/bin/plan lint`, `.claude/bin/plan status`, and
`.claude/bin/plan findings` first. Read `rev:` and `reviewed:` from the phase
frontmatter to choose exactly one review scope.

- If `reviewed:` is absent, this is the first pass. Run **First review**.
- If `reviewed:` is lower than `rev:`, this is a revised plan. Run
  **Revision review**.
- If `reviewed:` equals or exceeds `rev:`, this revision has already been
  reviewed. Run `.claude/bin/plan recommend`, print it, and stop without
  reading or writing anything else.

You did not write the plan or the revisions you are reviewing.

## First review

Read PLAN.md, the phase file it points at, AGENTS.md, and the codebase. Review
the phase as an independent senior engineer inheriting someone else's work.
Be skeptical.

Treat every E-code from the linter as a Critical finding and every W-code as
at least Medium. For each issue found, provide:
- Finding ID (F1, F2, ...)
- Severity: Critical, High, Medium, or Low
- Category: Missing work / Incorrect assumption / Risk / Task ordering /
  Architectural issue / Missing acceptance criteria / Unnecessary scope /
  Wrong file list
- Affected task ID(s)
- Description
- Recommended fix

Beyond the linter, which only checks shape:
- Treat any unresolved open question from the plan as Critical.
- Treat any task whose Verify line is not a runnable command or a named
  screen as High.
- Check every `files` list against the codebase. A task that will obviously
  need a file it does not list is High: it will stall a bounded build session.
- Check the dependency edges are true. The linter proves the graph is
  acyclic, not that T4 actually needs T2.
- Review the phase ordering in PLAN.md too, not just the tasks in this phase.

Order findings by impact. Do not inflate severity to look thorough — a Medium
labeled Critical is itself a review failure. If nothing rises above Medium,
say so and give the two things most likely to break anyway.

## Revision review

Read the phase file's `## Changelog` and frontmatter, and only the tasks the
changelog names. Do not re-review the phase end to end: the first pass already
did that, and the revision-stamped changelog defines what changed.

For each finding the changelog claims `resolved` or `accepted`, decide:
actually resolved, partially resolved, or not resolved. Quote the plan line
that settles it. A note that does not name a task ID or plan line is not
evidence; reopen that finding:

  .claude/bin/plan resolve F2 open "worker.ts still missing from T4 files"

Then check only three things beyond that:
- Did any resolution create a new dependency, ordering, or scope problem?
  Record it as a new finding with the next free F-id.
- Did any resolution change what a task touches without updating its `files`
  list?
- Did any Medium marked `accepted` get a real reason, or a restatement of the
  finding?

## Record findings

Findings only in this session's transcript are findings /cs-revise and the
next review cannot read. Reason in plan mode, then exit plan mode and append
new findings to the phase file's `## Findings` section, one line per finding,
seven fields:

  F1 | Critical | Task ordering | T3 | open | description | recommended fix

Continue the existing finding numbering. Every new finding starts `open`.
Use `-` in the task field for a plan-level finding. No pipes inside the
description or fix — the parser splits on them, and `plan lint` will reject
the line. If the phase file has no `## Findings` section, add one.

The Findings section, changelog entries written by `plan resolve`, and
`plan reviewed` are the only writes you make. Do not rewrite the plan, resolve
your own new findings, or touch the task graph; /cs-revise does that.

## Finishing

1. `.claude/bin/plan reviewed` — record that this rev had a review pass.
2. `.claude/bin/plan lint` — confirm the findings and resolutions parse.
3. `.claude/bin/plan recommend` and print it. Open findings send you to
   /cs-revise; a clean pass sends you to /cs-approve. At rev 3 with a Critical
   still open, follow the stop condition and split the phase instead.
4. After a revision review, end with one line naming what this pass did not
   inspect.
5. Stop. /cs-revise can run in this session, but the review after it must run
   in a new one.
