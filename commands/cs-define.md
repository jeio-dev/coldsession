---
description: Turn a rough idea into a durable, planning-ready OBJECTIVE.md
argument-hint: [idea] [--revise] [--resume]
---

Create or intentionally revise the repository-root `OBJECTIVE.md`.

Interpret `$ARGUMENTS` as follows:

- No `--revise`: the remaining text is the rough idea.
- `--revise`: intentionally revise the existing objective using the remaining
  text as the requested change.
- `--resume` is valid only when `OBJECTIVE.md` says `active: define`.

## Entry guard

Check file existence before reading repository content.

1. If `PLAN.md` exists, stop without opening `OBJECTIVE.md`. Product scope is
   frozen once planning starts; objective changes now belong in a future phase.
2. If `OBJECTIVE.md` exists and `--revise` is absent, stop without opening it.
   Tell me to run the next command it enabled, or explicitly use
   `/cs-define --revise <change>` before planning.
3. If `--revise` is present but `OBJECTIVE.md` is absent, stop; there is
   nothing to revise.
4. If `active: define` exists, a plain invocation stops. Only the same command
   with `--revise --resume` may continue.
5. If the idea or requested change is blank, ask for it and stop.

For an intentional revision, read `OBJECTIVE.md`, set `active: define` before
substantive work, preserve unchanged decisions, and increment `objective-rev`
exactly once when the revision is complete. Remove `active:` in the same edit.

## Define the objective

Discover facts before asking me for them. For an existing codebase, inspect
only repository guidance, architecture notes, README, and dependency manifests
needed to establish current constraints. Do not infer product intent from code.

Ask direct questions for every missing decision that would materially change
scope, users, constraints, or success. Do not guess. Distinguish a confirmed
decision from an assumption I explicitly accept.

Write `OBJECTIVE.md` from `templates/OBJECTIVE.md` only after all blocking
questions are answered. Write it once at the end, not incrementally. It must
contain:

- A concrete problem and named primary user.
- A one- or two-sentence outcome-focused value proposition.
- One smallest end-to-end primary journey: trigger, essential steps, result.
- The minimum MVP capabilities that make that journey work.
- Explicit v1 exclusions that do not overlap the MVP.
- Concrete constraints, or `None` where deliberately unconstrained.
- Observable success criteria. "Works", "fast", and "user friendly" are not
  criteria unless a measurable threshold or named observation defines them.
- Only non-blocking assumptions.
- `## Open questions` containing exactly `None.`

Reject placeholders, TODOs, implementation phases, task breakdowns, and
unanswered alternatives. Set `status: ready` only when another agent can plan
from this file without this session.

## Next

Choose from repository state:

- Empty or near-empty repo, or no AGENTS.md: `/cs-groundwork` in a new session.
- Existing codebase: `/cs-plan` in a new session.

Say that both commands read `OBJECTIVE.md` from disk, so this session should
end. From `/cs-plan` onward, `.claude/bin/plan recommend` computes the next
step from phase state.
