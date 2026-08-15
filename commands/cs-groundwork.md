---
description: Phase 0 scaffold and ground rules for a greenfield repo
---

This is a greenfield repo. Set up the ground rules before any feature work.

From the objective brief, write:

1. AGENTS.md, under 60 lines. One line on what this is, the stack, and the
   constraints that must never be violated. Leave the Commands section empty
   until the scaffold exists.
2. CLAUDE.md, containing @AGENTS.md plus any Claude Code specific lines.
3. docs/architecture.md: each decision from the brief with what was rejected
   and why. Not a stack list; package.json is the stack list.
4. docs/data-model.md: the schema, plus the ownership rules the schema does
   not express. Skip if there is no datastore.
5. PLAN.md from templates/PLAN.md, with this groundwork as Phase 0.

Do not invent conventions you have no basis for. If the brief does not
determine it, leave it out.

Then enforce in code what markdown cannot:
- .gitignore covering env files, build output, and local state
- .env.example, committed, keys only, no values
- lint, format, and typecheck installed and runnable
- one pre-commit or CI check that fails on a committed secret

Scaffold the project. Run every command you are about to put in AGENTS.md,
fix the ones that fail, and only then write them down.

Acceptance: I open a new session and ask what this project is and how to run
it. It answers from AGENTS.md alone, without reading source.

## Next

Commit the scaffold, then tell me to run `/cs-plan` for Phase 1 with the
objective brief. If PLAN.md now exists, run `.claude/bin/plan recommend` and
print it instead — from here the phase file decides, not the command.
