---
description: Independent review of the current phase, round 1
---

Run `.claude/bin/plan lint` and `.claude/bin/plan status` first. Treat every
E-code it prints as a Critical finding and every W-code as at least Medium,
then read PLAN.md, the phase file it points at, AGENTS.md, and the codebase.

You did not write this plan. Review it as an independent senior engineer
inheriting someone else's work. Be skeptical.

For each issue found, provide:
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

## Record them

Findings only in this session's transcript are findings /revise and /recheck
cannot read. Reason in plan mode, then exit plan mode and write them into the
phase file's `## Findings` section, one line per finding, seven fields:

  F1 | Critical | Task ordering | T3 | open | description | recommended fix

Every finding starts `open`. Use `-` in the task field for a plan-level
finding. No pipes inside the description or the fix — the parser splits on
them, and `plan lint` will reject the line. If the phase file has no
`## Findings` section, add one.

That section and `plan reviewed` are the only writes you make. Do not rewrite
the plan, do not resolve your own findings, and do not touch the task graph —
/revise does that.

Then:
1. `.claude/bin/plan reviewed` — records that this rev has had a review pass.
2. `.claude/bin/plan lint` — confirm the findings you wrote parse.
3. `.claude/bin/plan recommend` and print it. It will send you to /revise if
   you found anything, and to /approve if you did not.
4. Stop. /revise runs next, and it can run in this session.
