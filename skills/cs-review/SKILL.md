---
name: cs-review
description: Independently review one guarded coldsession phase revision and persist findings without revising the plan. Use in a fresh chat for $cs-review, changelog-scoped revision review, or explicit --resume recovery.
---

# Coldsession Review

Read `.agents/coldsession/commands/cs-review.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat accompanying flags as `$ARGUMENTS` and preserve `--resume` exactly.

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
