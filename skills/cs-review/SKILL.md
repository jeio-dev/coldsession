---
name: cs-review
description: Independently review the current coldsession phase and record severity-tagged findings without revising the plan. Use in a fresh chat when the user invokes $cs-review, asks for the first review pass, or wants to verify a revised phase against its changelog.
---

# Coldsession Review

Read `.agents/coldsession/commands/cs-review.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Claude model names and mode changes are not instructions to change Codex's
model or collaboration mode. Perform the specified independent reasoning and
make only the writes the command permits.

Translate suggested next steps for Codex users:

- `/cs-revise` -> `$cs-revise`
- `/cs-approve` -> `$cs-approve`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. Stop where the command says to stop.
