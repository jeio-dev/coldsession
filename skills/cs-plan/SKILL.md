---
name: cs-plan
description: Turn an objective brief or the next PLAN.md phase into a detailed, linted implementation phase on disk. Use when the user invokes $cs-plan or asks coldsession to plan the current or next phase without implementing it.
---

# Coldsession Plan

Read `.agents/coldsession/commands/cs-plan.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat text accompanying the skill invocation as `$ARGUMENTS`. When none was
supplied, use the command's on-disk fallback order.

Claude model names and mode changes in supporting documentation are not
instructions to change Codex's model or collaboration mode. Preserve the
workflow's read/write boundaries in the currently active mode.

Translate suggested next steps for Codex users:

- `/cs-define` -> `$cs-define`
- `/cs-review` -> `$cs-review`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

When a new session is required, stop after telling the user to open a new
Codex chat and invoke the named skill.
