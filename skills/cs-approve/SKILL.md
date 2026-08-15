---
name: cs-approve
description: Produce a guarded readiness checklist, persist actionable gaps, and mark a reviewed revision ready without approving it. Use in a fresh chat for $cs-approve or explicit --resume recovery.
---

# Coldsession Approve

Read `.agents/coldsession/commands/cs-approve.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat accompanying flags as `$ARGUMENTS` and preserve `--resume` exactly.

Translate suggested next steps for Codex users:

- `/cs-revise` -> `$cs-revise`
- `/cs-build Tn` -> `$cs-build Tn`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. Preserve the human approval gate: do not set `status: approved`.
