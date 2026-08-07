---
description: Readiness checklist with evidence, no verdict
---

Run `.claude/bin/plan lint`, then read the phase file and its changelog. You
did not write either. Do not approve or reject. Produce the readiness
checklist only.

For each line, give PASS or FAIL plus the evidence — quote the finding ID,
task ID, linter output, or plan line that proves it. "Looks fine" is a FAIL.

- The linter exits clean.
- Every Critical and High finding has a changelog entry, and the plan line it
  points at actually contains the fix.
- Every task has acceptance criteria and a Verify line I could run today.
- Every task's `files` list is complete enough that a session bounded to it
  could finish the task.
- Every remaining Medium/Low finding is explicitly accepted or justified.
- The phase ends in a state I can run.

Then list, in one line each, the riskiest thing still in the plan.

Do not set `status: approved`. I do that.
