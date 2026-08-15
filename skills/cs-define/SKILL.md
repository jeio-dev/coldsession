---
name: cs-define
description: Turn a rough product or feature idea into a durable, planning-ready OBJECTIVE.md without writing code. Use before groundwork or initial planning when the user invokes $cs-define, or intentionally revises a pre-plan objective with --revise.
---

# Coldsession Define

Read `.agents/coldsession/commands/cs-define.md` completely and follow its workflow.
Resolve `.agents/coldsession/commands/cs-define.md` from the repository root and perform the
workflow with that root as the working directory.

Treat the text accompanying the skill invocation as `$ARGUMENTS`. If no idea
was supplied, ask for it and stop as the command instructs.

Preserve `--revise` and `--resume` flags exactly when passing arguments to the
canonical workflow.

Translate every suggested Claude command for Codex users:

- `/cs-groundwork` -> `$cs-groundwork`
- `/cs-plan` -> `$cs-plan`

When reporting a next step, show the Codex skill name. You may also show the
Claude slash command in parentheses when the repository is used by both.
