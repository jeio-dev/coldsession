---
name: cs-grant
description: Report the result of a human approval typed as $cs-grant, which the prompt hook applies before the turn. Use only when the user invokes $cs-grant; never approve a phase yourself.
---

# Coldsession Grant

Read `.agents/coldsession/commands/cs-grant.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Translate the slash command in the tool's final `next` line to its Codex
skill equivalent: keep any arguments and prefix the command name with `$`.
Show the Codex form first and optionally the original Claude slash command in
parentheses. Preserve the human approval gate: do not set `status: approved`.
