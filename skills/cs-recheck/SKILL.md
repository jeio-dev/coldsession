---
name: cs-recheck
description: Deprecated explicit compatibility alias for cs-review. Use only when the user directly invokes $cs-recheck; route the request through the state-aware review workflow.
---

# Coldsession Recheck Compatibility Alias

Read `.agents/coldsession/commands/cs-review.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat this as `$cs-review`, not as a separate workflow stage. Show
`$cs-review` as the canonical command in every next step.

Treat accompanying flags as the review command's `$ARGUMENTS` and preserve
`--resume` exactly.

Translate suggested next steps for Codex users:

- `/cs-review` -> `$cs-review`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. Stop where the command says to stop.
