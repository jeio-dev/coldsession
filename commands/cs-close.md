---
description: Guarded phase audit and close
argument-hint: [--resume]
---

First run `.claude/bin/plan begin close $ARGUMENTS` and inspect only its output.
If it refuses, print that output and stop. Close begins only for an approved
phase whose tasks are all done; an interrupted close requires `--resume`.

Read the phase's commits, its log, and the complete phase including findings.
List only corrections that happened more than once or failures caused by
missing repository guidance. Tie each to a commit, log entry, or finding and
propose exactly one durable home: AGENTS.md globally, a directory rule, or a
skill for a repeated procedure.

Audit the delivered phase against every acceptance criterion and report gaps,
dead code, and unwired work. If the audit finds a material gap, add a
deduplicated open finding, run `.claude/bin/plan finish close --fail`, print
`plan recommend`, and stop without closing.

If clean, run `.claude/bin/plan finish close --pass`. It atomically ticks this
phase in PLAN.md, sets `status: closed`, clears the marker, and leaves
`current:` on the closed phase.

If PLAN.md has another unchecked phase, name and quote it and tell me to run
`/cs-plan` in a new session. Plan reads the closed phase and log, never
OBJECTIVE.md. If none remains, say the plan is complete.
