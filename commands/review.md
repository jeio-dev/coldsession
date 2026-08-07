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

Do not rewrite the plan.
