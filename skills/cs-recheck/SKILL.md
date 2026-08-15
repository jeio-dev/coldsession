---
name: cs-recheck
description: Recheck a revised coldsession phase against its changelog and reopen unsupported resolutions. Use in a fresh chat when the user invokes $cs-recheck or asks for review round two or later.
---

# Coldsession Recheck

Read `.agents/coldsession/commands/cs-recheck.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Translate suggested next steps for Codex users:

- `/cs-revise` -> `$cs-revise`
- `/cs-approve` -> `$cs-approve`
- `/cs-plan` -> `$cs-plan`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. Stop where the command says to stop.
