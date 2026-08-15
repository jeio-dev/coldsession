---
description: Phase 0 scaffold and ground rules from OBJECTIVE.md
argument-hint: [--resume]
---

Set up a greenfield repository from root `OBJECTIVE.md`.

## Entry guard

- If `PLAN.md` exists, stop before opening `OBJECTIVE.md`; Groundwork already
  finished. Run `.claude/bin/plan recommend` and print it.
- Require `OBJECTIVE.md` with `status: ready`. If it is absent or not ready,
  stop and tell me to run `/cs-define`.
- If it says `active: groundwork`, a plain invocation stops. Continue only
  with `--resume`.
- Any other `active:` value stops and names that active command.

Set `active: groundwork` in `OBJECTIVE.md` before substantive work. A resumed
run inspects what is already present and continues; it does not recreate or
overwrite correct scaffold files.

From `OBJECTIVE.md`, write:

1. AGENTS.md, under 60 lines. One line on what this is, the stack, and the
   constraints that must never be violated. Leave Commands empty until the
   scaffold exists.
2. CLAUDE.md, containing @AGENTS.md plus Claude Code-specific lines.
3. docs/architecture.md: each chosen decision, what was rejected, and why.
4. docs/data-model.md: schema plus ownership rules the schema cannot express.
   Skip it when there is no datastore.

Do not invent conventions the objective and repository do not establish.

Then enforce in code what markdown cannot:

- .gitignore covering environment files, build output, and local state.
- .env.example, committed, with keys only and no values.
- Runnable lint, format, and typecheck commands.
- One pre-commit or CI check that fails on a committed secret.

Scaffold the project. Run every command before putting it in AGENTS.md and fix
failures first.

## Completion boundary

Only after the scaffold passes:

1. Write a valid closed `docs/plans/00-groundwork.md` recording the completed
   scaffold tasks and their real Verify commands.
2. Create `PLAN.md` with `current:` pointing to Phase 00, a checked Phase 00
   line, `objective-rev:` copied from `OBJECTIVE.md`, and provisional unchecked
   product phases derived from the objective in dependency order.
3. Remove `active: groundwork` from `OBJECTIVE.md`.

Create `PLAN.md` last. Its existence is the durable completion marker and lets
the next `/cs-plan` work only from phase state without rereading the objective.

Acceptance: a new session can identify the project and run its checks from
AGENTS.md alone, and `.claude/bin/plan lint` accepts Phase 00.

## Next

Commit the scaffold, run `.claude/bin/plan recommend`, print it, and tell me to
run the named `/cs-plan` in a new session.
