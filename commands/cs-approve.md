---
description: Guarded readiness checklist with persisted gaps, no verdict
argument-hint: [--resume]
---

First run `.claude/bin/plan begin approve $ARGUMENTS` and inspect only its
output. If it refuses, print that output and stop without reading the plan.

Run `.claude/bin/plan lint`, `.claude/bin/plan status`, and
`.claude/bin/plan findings`, then read the phase and Changelog. You did not
write them. Do not approve, reject, or revise task content.

For each line give PASS or FAIL with a finding ID, task ID, linter output, or
quoted plan line as evidence. "Looks fine" is a FAIL.

- The linter exits clean.
- `plan findings --open` prints nothing.
- Every Critical and High has a changelog entry and the named plan line carries
  the fix.
- Every task has acceptance criteria and a runnable Verify line.
- Every task's `files` list can bound a complete Build session.
- Every remaining Medium or Low is explicitly accepted with a real reason.
- The phase ends in a runnable state.

For the single highest residual risk, report one line containing all four:

  Risk — impact — mitigation with task/line evidence — exact remaining action

If the mitigation is sufficient, say `remaining action: none` and cite it. If
it is not, this checklist FAILs.

## Persist every actionable failure

For each FAIL or unmitigated material risk not already represented, append one
deduplicated open finding to Findings:

  F(n) | <severity> | <category> | <tasks-or-> | open | gap and impact | exact plan edit that resolves it

Do not leave a gap only in this transcript: `/cs-revise` reads on-disk open
findings, not pasted feedback. Then run `.claude/bin/plan lint` and
`.claude/bin/plan finish approve --fail`, print `plan recommend`, and tell me
to run Revise followed by Review in a new session.

If every line passes, run `.claude/bin/plan finish approve --pass`. This writes
`ready: <rev>` and clears the marker; it does not approve. Tell me to set
`status: approved` myself. Run `.claude/bin/plan next`, name the first ID, and
tell me to use `/cs-build T(n)` in a new session. A repeated Approve stops at
the ready marker while waiting for the human edit.
