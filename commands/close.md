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

Finally: tick this phase in PLAN.md, and set `status: closed` in the phase
file's frontmatter. Leave `current:` pointing at this phase. /plan moves it
when it writes the next phase file, so the pointer never names a file that
does not exist yet.

## Next

- A next phase exists in PLAN.md: tell me to run `/plan` for it in a NEW
  session. Name the phase and quote its PLAN.md line, so I can paste it if I
  want to. /plan reads this closed phase and its log for what carries
  forward, and asks its open questions before it writes. Do not send me to
  /define; the product scope was settled before Phase 01.
- No phase left: say the plan is complete, and do not invent one.

The new phase file starts unreviewed, so `plan recommend` picks the loop up
from /review on its own once /plan has written it.
