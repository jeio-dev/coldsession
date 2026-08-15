---
name: cs-build
description: Start or explicitly resume, implement, verify, and commit one approved coldsession task using its bounded read list. Use for $cs-build with a task ID, including --resume recovery.
---

# Coldsession Build

Read `.agents/coldsession/commands/cs-build.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat the task ID and optional `--resume` accompanying the skill invocation as
`$ARGUMENTS`. If no ID was supplied, follow the blank-argument path.

If the command asks for a search subagent but subagents are unavailable or
not authorized, use a bounded read-only search and retain only the required
`file:line` result in working context.

Translate suggested next steps for Codex users:

- `/cs-build Tn` -> `$cs-build Tn`
- `/cs-close` -> `$cs-close`
- `/cs-revise` -> `$cs-revise`
- Any other slash command printed by `plan recommend` maps to the skill with
  the same `cs-` name, with `/` replaced by `$`.

When the command says to exit the session, stop after telling the user to
open a new Codex chat and invoke the named skill.
