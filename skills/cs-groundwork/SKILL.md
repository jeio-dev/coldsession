---
name: cs-groundwork
description: Establish a guarded Phase 0 and scaffold a greenfield repository from OBJECTIVE.md. Use when the user invokes $cs-groundwork, resumes it with --resume, or asks coldsession to prepare an empty project before planning.
---

# Coldsession Groundwork

Read `.agents/coldsession/commands/cs-groundwork.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat accompanying flags as `$ARGUMENTS` and preserve `--resume` exactly.

This repository supports both agents. Create `AGENTS.md` as the shared source
of project instructions and keep the requested `CLAUDE.md` bridge for Claude
Code. Do not add Codex-only global configuration.

Translate suggested next steps for Codex users:

- `/cs-plan` -> `$cs-plan`
- Any slash command printed by `plan recommend` maps to the skill with the
  same `cs-` name, with `/` replaced by `$`.

Show the Codex skill name first and optionally the Claude command in
parentheses.
