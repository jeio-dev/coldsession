---
name: cs-revise
description: Resolve recorded coldsession plan findings in place and update the revision changelog. Use when the user invokes $cs-revise or asks to revise a reviewed phase that has open findings.
---

# Coldsession Revise

Read `.agents/coldsession/commands/cs-revise.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Translate suggested next steps for Codex users:

- `/cs-recheck` -> `$cs-recheck`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. When the command requires a new session, stop after telling the
user to open a new Codex chat and invoke the named skill.
