---
name: cs-fanout
description: Build one file-disjoint group of approved coldsession tasks as supervised parallel workers in Orca, then report their outcomes. Use for $cs-fanout, or when the user asks to build several ready tasks at once, in parallel, or across several sessions.
---

# Coldsession Fanout

Read `.agents/coldsession/commands/cs-fanout.md` completely and follow its workflow.
Resolve it from the repository root and perform the workflow with that root
as the working directory.

Treat any `--max N` accompanying the skill invocation as `$ARGUMENTS`.

Two substitutions for the Codex surface:

- Start workers with `--agent codex --model <codex-model-id> --effort medium`
  in place of `--agent claude --model sonnet --effort medium` — `worker-start`
  takes launch-time model and effort for Codex exactly as it does for Claude
  (`--model supports Claude, Codex, and Cursor opaque provider model ids`; use
  whatever Codex model id this project's Codex sessions already launch with).
  If the worker server's `worker-start` rejects `--model`/`--effort` outright
  (an older Orca runtime that never advertised launch-preference support for
  that server), drop both flags for that dispatch, launch the worker at
  whatever default it gets, and say so plainly in the close-out report rather
  than silently treating it as medium effort.
- Write the worker's build command as `$cs-build <id>`, and map any other
  slash command the same way: same `cs-` stem, `$` for `/`. Quote it literally
  (single quotes) in `--spec`: unquoted or double-quoted, a shell expands `$cs`
  to nothing and leaves `-build <id>`, not `$cs-build <id>`.

The bounded read list is the load-bearing rule here and Codex has no hook to
enforce it, so the dispatch spec must state it rather than assume it. A worker
that needs a file its brief omits raises it with
`orca orchestration ask` — widening its own reads is the one thing it may not do.

You are the coordinator. Do not build a task yourself, and do not mark one done
on a worker's behalf.
