---
name: cs-approve
description: Produce the coldsession evidence checklist for plan readiness without issuing the approval verdict. Use in a fresh chat when the user invokes $cs-approve or asks whether a reviewed phase is ready to approve.
---

# Coldsession Approve

Read `.agents/coldsession/commands/cs-approve.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Translate suggested next steps for Codex users:

- `/cs-revise` -> `$cs-revise`
- `/cs-build Tn` -> `$cs-build Tn`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses. Preserve the human approval gate: do not set `status: approved`.
