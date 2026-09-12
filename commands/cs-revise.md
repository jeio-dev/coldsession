---
description: Resolve findings in one guarded revision and write the changelog
argument-hint: [--resume]
---

First run `.claude/bin/plan begin revise $ARGUMENTS` and inspect only its
output. If it refuses, print that output and stop. A matching interrupted pass
continues only with `--resume`.

Run `.claude/bin/plan findings --open` and inspect the phase metadata and the
named findings. Record the initial `git status --short` so this session's
changes can be committed separately from unrelated work.

For format 2 only: if every open finding is Low and merits acceptance, leave
the specification and implementation unchanged, do not bump, and record each
acceptance with its concrete reason through `.claude/bin/plan resolve`. Finish
with `.claude/bin/plan lint` and `.claude/bin/plan finish revise --accept-only`.
This preserves the existing review and routes to the independent approval
checklist. It never grants approval. On resume, use this path only if no bump
or substantive edit occurred. If the runtime refuses it, use the normal path.

Otherwise run `.claude/bin/plan bump` before edits or settlements. It increments
once for a new Revise pass and is a safe no-op on resume; never hand-edit `rev:`.

Revise the current phase in place. Do not create a replacement file. Update
PLAN.md only when a finding changes phase ordering.

- Resolve every Critical and High.
- Resolve each Medium or explicitly accept it with a concrete reason.
- Accept a Low with a concrete reason by default when its own evidence shows
  the implementation and required behavior are correct and the issue is only
  descriptive wording. Fix Lows with a real consequence. Do not change prose
  solely to avoid using `accepted`.
- Preserve task IDs where possible and keep graph entries and task sections in
  sync when tasks change.

After the edit, close each addressed finding through the runtime:

  .claude/bin/plan resolve F1 resolved "T3 now depends on T2"
  .claude/bin/plan resolve F3 accepted "T2 exports rows; the types line stays"

`resolved` names a verified change that satisfies the finding's stated ask.
`accepted` names the remaining issue, why its consequence is tolerable, and
the task/line or evidence supporting that decision. Never write "done" or
"fixed". Keep notes on one line without pipes. Leave genuinely unresolved
findings open and explain why.

When a finding has reopened twice, compare its exact ask with prior settlements
before doing more verification. Name the target and quote the changed line in
the resolution note, redacting sensitive values. Repeating a live check does
not resolve a requested deletion. If the ask cannot be located, keep it open
and record the missing target; do not claim resolution.

Finish with:

1. `.claude/bin/plan lint` — fix errors introduced by the revision.
2. `.claude/bin/plan finish revise` — persist the revision and changelog and
   clear the active marker. The acceptance-only path uses its finish above.
3. After finish succeeds, inspect the diff and commit this session's phase,
   index, and other authorized changes together. Stage explicit paths or hunks;
   preserve unrelated existing work and staged changes. Include the phase and
   revision in the message. Check `git status --short`; report any remaining
   changes or commit failure without claiming the work is committed. Do not
   require a globally clean tree when unrelated work was present. Apply this
   step to the acceptance-only path too. Follow an explicit project/user
   no-commit instruction if one exists and report the pending commit instead.
4. `.claude/bin/plan recommend` and print it. An unreviewed revision always
   returns to `/cs-review`, even when a finding remains open.
5. Stop and exit. Review must run in a new session.
