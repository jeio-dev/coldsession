---
name: cs-define
description: Turn a rough product or feature idea into a scoped objective brief without writing code. Use at the start of the coldsession workflow, before groundwork or planning, when the user invokes $cs-define or asks to define an idea with coldsession.
---

# Coldsession Define

Read `.agents/coldsession/commands/cs-define.md` completely and follow its workflow.
Resolve `.agents/coldsession/commands/cs-define.md` from the repository root and perform the
workflow with that root as the working directory.

Treat the text accompanying the skill invocation as `$ARGUMENTS`. If no idea
was supplied, ask for it and stop as the command instructs.

Translate every suggested Claude command for Codex users:

- `/cs-groundwork` -> `$cs-groundwork`
- `/cs-plan` -> `$cs-plan`

When reporting a next step, show the Codex skill name. You may also show the
Claude slash command in parentheses when the repository is used by both.
