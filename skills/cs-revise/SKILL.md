---
name: cs-revise
description: Resolve recorded coldsession findings in one guarded, idempotent revision and update its changelog. Use for $cs-revise, open reviewed findings, or explicit --resume recovery.
---

# Coldsession Revise

Read `.agents/coldsession/commands/cs-revise.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat accompanying flags as `$ARGUMENTS` and preserve `--resume` exactly.

Translate suggested next steps for Codex users:

- `/cs-review` -> `$cs-review`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. When the command requires a new session, stop after telling the
user to open a new Codex chat and invoke the named skill.
