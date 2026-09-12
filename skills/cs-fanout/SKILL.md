---
name: cs-fanout
description: Explicitly dispatch one approved group through Orca, Codex native subagents, or Claude agent teams. Use only when the user invokes cs-fanout or requests team execution.
---

Read `.agents/coldsession/commands/cs-fanout.md` completely and follow it from
the repository root. Pass `--backend` and `--max` as invocation arguments.
Translate Claude slash command names to matching Codex skills. Use the native
Codex backend when selected and available; preserve the worker contract and
coordinator-only workflow mutations. Do not infer capability from CLI presence.
