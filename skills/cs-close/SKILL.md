---
name: cs-close
description: Audit delivered work, harvest repeated corrections, and close a completed coldsession phase. Use in a fresh chat when the user invokes $cs-close or asks to close a phase whose tasks are all done.
---

# Coldsession Close

Read `.agents/coldsession/commands/cs-close.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

This repository supports both agents. When proposing persistent guidance,
use the shared root `AGENTS.md` for repository-wide guidance. For
directory-scoped guidance, mention both a nested `AGENTS.md` for Codex and a
`.claude/rules/` rule for Claude Code; do not create either without the
user's approval because this step only proposes corrections.

Translate suggested next steps for Codex users:

- `/cs-plan` -> `$cs-plan`
- `/cs-define` -> `$cs-define`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

When a new session is required, stop after telling the user to open a new
Codex chat and invoke the named skill.
