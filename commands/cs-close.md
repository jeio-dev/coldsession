---
description: Guarded phase audit and close
argument-hint: [--resume]
---

First run `.claude/bin/plan begin close $ARGUMENTS` and inspect only its output.
If it refuses, print that output and stop. Close begins only for an approved
phase whose tasks are all done; an interrupted close requires `--resume`.

Record the initial `git status --short`. Read the phase's commits, its log,
and the complete phase including findings.
A correction earns a line only on its second occurrence — the first time is
signal, not yet a pattern, even when it was caused by missing repository
guidance. Tie each to the two commits, log entries, or findings where it
happened and propose exactly one durable home: AGENTS.md globally, a
directory rule, or a skill for a repeated procedure. If AGENTS.md is already
at its 60-line budget (`plan lint` warns `W06` past that), name the existing
line the new one replaces instead of appending — growth stays bounded by
construction, not by memory.

Audit the delivered phase against every acceptance criterion and report gaps,
dead code, and unwired work. If CI is required, verify an actual run's tested
commit and required job conclusions, and check later changes against the CI
inputs. Local results and branch pushes are not evidence of a CI run.
If the audit finds a material gap, add a
deduplicated open finding, run `.claude/bin/plan finish close --fail`, print
`.claude/bin/plan recommend`, commit the persisted findings as described below,
and stop without closing.

If clean, run `.claude/bin/plan finish close --pass`. It atomically ticks this
phase in PLAN.md, sets `status: closed`, clears the marker, and leaves
`current:` on the closed phase.

After finish succeeds (pass or fail), inspect the diff and commit this session's
phase, PLAN.md, and authorized log/evidence changes together. Stage explicit
paths or hunks and preserve unrelated work and staged changes. Include the
phase and close outcome in the message. Check `git status --short` and report
remaining changes or a failed commit. A globally clean tree is not required
when unrelated work was present. If the project/user explicitly prohibits
commits, report the pending commit instead. CI evidence recorded later needs
its own commit; reassess CI inputs without calling an earlier commit the
session's last act.

If PLAN.md has another unchecked phase, name and quote it and tell me to run
`/cs-plan` in a new session. Plan reads the closed phase and log, never
OBJECTIVE.md. If none remains, say the plan is complete.
