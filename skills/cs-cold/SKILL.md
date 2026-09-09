---
name: cs-cold
description: Hand the next coldsession step to a genuinely new agent session spawned in an Orca terminal, then stop. Use for $cs-cold, or when the user asks to run the next step cold, in a new session, or in another terminal.
---

# Coldsession Cold Handoff

Read `.agents/coldsession/commands/cs-cold.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat any command accompanying the skill invocation as `$ARGUMENTS`. If none
was supplied, follow the blank-argument path and take the command from
`plan recommend`.

Two substitutions for the Codex surface:

- Launch `codex` rather than `claude`. Collaboration mode still follows the
  active session, but model and reasoning effort are launch flags on Codex
  too, not session state (`codex --help`: `-m/--model`, `-c key=value`), so
  they need the same care as the Claude launch table. For `/cs-build`, launch
  `codex -c model_reasoning_effort=medium` to match that row's `--effort
  medium` (no quotes around `medium`: this whole string still has to sit
  inside the outer `--command "<launch>"` double quotes, and a nested `"`
  splits into two arguments on PowerShell). For every other row, Codex has no
  equivalent flag in the table, so launch the plain `codex` command. Say in
  the report which settings the new session should be given.
- Send the Codex form of the command: `/cs-review` -> `$cs-review`, and the
  same for every other `cs-` name. Quote it literally (single quotes) when it
  goes into `--title`/`--text`: unquoted or double-quoted, a shell expands
  `$cs` to nothing and leaves `-review`, not `$cs-review`.

The independence this buys is real on both surfaces, but only Claude Code
enforces it. Codex has no hook to refuse a judging command in the session that
authored the plan, so here the rule holds because you follow it: having spawned
the new session, stop. Do not also run the step in this one.
