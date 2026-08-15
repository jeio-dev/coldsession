---
description: State-aware independent review of the current phase
argument-hint: [--resume]
---

First run `.claude/bin/plan begin review $ARGUMENTS` and inspect only its
output. If it refuses, print that output and stop without reading anything
else. A matching interrupted pass continues only with `--resume`.

After entry succeeds, run `.claude/bin/plan lint`, `.claude/bin/plan status`,
and `.claude/bin/plan findings`. Read `rev:` and `reviewed:` to choose one
scope:

- `reviewed:` absent: **First review**.
- `reviewed:` lower than `rev:`: **Revision review**.

You did not write the plan or revision. Be skeptical. On `--resume`, inspect
existing findings before recording more and do not duplicate the same issue.

## First review

Read PLAN.md, the current phase, AGENTS.md, and the codebase using targeted
search. Treat every linter E-code as Critical and W-code as at least Medium.

For every issue record: ID, severity, category, affected task IDs, description,
and concrete recommended fix. Check especially:

- Unresolved open questions: Critical.
- Verify lines that are neither runnable commands nor named visual checks: High.
- Incomplete `files` lists against the real codebase: High.
- False or missing dependency edges.
- Phase ordering in PLAN.md, unnecessary scope, and missing runnable outcomes.

Do not inflate severity. If nothing exceeds Medium, say so and name the two
most likely failure points.

## Revision review

Read the current revision's Changelog and only the tasks its entries name.
For each `resolved` or `accepted` finding, decide whether it is actually,
partially, or not resolved and quote the settling plan line. Reopen unsupported
claims with `plan resolve F2 open "T4 line still omits worker.ts"`.

Beyond those lines, check only whether a resolution created a dependency,
ordering, or scope problem; changed touched files without changing `files`;
or accepted a Medium without a real reason. Record new issues with the next
free finding ID.

## Record and finish

Append each new finding once to Findings in the seven-field shape:

  F1 | Critical | Task ordering | T3 | open | description | recommended fix

Use `-` for a plan-level finding and no pipes inside prose. Findings,
changelog entries made by `plan resolve`, and runtime stage metadata are the
only writes. Do not revise the plan or resolve your own new findings.

Then run:

1. `.claude/bin/plan finish review` — atomically records `reviewed:` and clears
   the active marker.
2. `.claude/bin/plan lint`.
3. `.claude/bin/plan recommend` and print it.

After a revision review, name what the scoped pass did not inspect. Stop. A
recommended Revise may run here, but its following Review must use a new session.
