---
name: cs-status
description: Report the current coldsession phase, progress, findings, runnable tasks, blockers, and computed next action without reading source files. Use when the user invokes $cs-status or asks where the workflow stands.
---

# Coldsession Status

Read `.agents/coldsession/commands/cs-status.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Translate the slash command in the tool's final `next` line to its Codex
skill equivalent: keep any arguments and prefix the command name with
`$`. Because the command already starts with `cs-`, both agents use the same
stem. Show the Codex form first and optionally the original Claude
slash command in parentheses.
