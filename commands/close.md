---
description: Harvest repeated corrections, then close the phase
---

Run `.claude/bin/plan status`. If any task is not done, stop, say which, and
print `.claude/bin/plan recommend` — it names what to run instead.

Read this phase's commits, its log file, and the phase file including every
finding.

List the things I had to correct more than once across the phase, or that a
session got wrong because the repo never told it otherwise. Ignore one-off
mistakes.

For each, propose exactly one of:
- a line for AGENTS.md, if it applies everywhere
- a rule in .claude/rules/, if it only applies to one directory
- a skill, if it's a procedure we ran at least twice

Propose nothing you can't tie to a specific commit, log entry, or finding.

Then audit the delivered phase against its acceptance criteria and report
gaps, dead code, and anything left unwired.

Finally: tick this phase in PLAN.md and advance `current:` to the next phase
file.

## Next

- A next phase exists in PLAN.md: tell me to run `/plan` for it in a NEW
  session, and `/define` first if its objective is more than one line in
  PLAN.md. The new phase file starts unreviewed, so `plan recommend` will
  pick the loop up from /review on its own.
- No phase left: say the plan is complete, and do not invent one.
