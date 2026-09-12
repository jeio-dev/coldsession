---
description: Independently review the current phase and revise it when findings require changes
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
search. Repair structural linter errors before proceeding. Warnings are advisory and do not
automatically become blocking findings. A finding must identify a concrete defect
or unnecessary complexity and its consequence. A clean review is valid.

For every issue record: ID, severity, category, affected task IDs, description,
and concrete recommended fix. Check especially:

- Unresolved open questions: Critical.
- Verify lines that are neither runnable commands nor named visual checks: High.
- Incomplete `files` lists against the real codebase: High.
- False or missing dependency edges.
- Phase ordering in PLAN.md and missing runnable outcomes.
- Claims that a gate passed: distinguish a local result from an actual CI run.
  When CI is required for delivered work, identify the run, tested commit, and
  required job conclusions. Before implementation, check that the planned
  trigger and evidence collection can establish this; do not demand a run of
  code that has not been built yet.
- Unnecessary scope: name the rung the task should have stopped at (existing
  capability, configuration change, extension, new file, new abstraction) and
  make that rung the recommended fix. Medium by default; High when the
  over-build widens `files` past what the goal needs, because that spends Build
  context directly.
- Policy: list the project's own `policy-*` skills yourself — `.claude/skills/`
  under Claude Code, `.agents/skills/` under Codex — and read the ones this
  phase can violate. Do not take the phase's `## Policy` section as the list;
  it is the judgement you are checking. File each miss under the category
  `Policy`: a task that breaks an applicable policy, an applicable policy the
  phase never addressed, or a `## Policy` line claiming coverage no task
  carries. Severity is the policy's own stakes, not the category's — a
  security, privacy, or compliance breach is Critical or High; a brand or copy
  deviation is usually Medium. A project with no `policy-*` skill has no policy
  layer, and its absence is never a finding.

Do not inflate severity or invent failure points. Record independent findings
before discussing them with the author. Use neutral requirements and artifacts,
without author advocacy or prior discussion. If the review is clean, say so.

## Revision review

Read the current revision's Changelog and only the tasks its entries name.
For each finding settled in the current revision, verify its stated disposition:
`resolved` needs evidence that the exact ask was addressed; `accepted` needs
a concrete reason why the remaining consequence is tolerable. Acceptance does
not claim a fix. Let a reasoned acceptance stand unless evidence contradicts
its premise or shows a material consequence the reason did not address.
Reopen unsupported claims with
`.claude/bin/plan resolve F2 open "T4 line still omits worker.ts"`.

Beyond those lines, check only whether a resolution created a dependency,
ordering, scope, or policy problem; changed touched files without changing
`files`; or introduced an unsupported acceptance. If a fix adds a verification
heuristic or decision rule, test that rule against a counterexample and the
actual gate. Record new issues with the next free finding ID only when they
have a concrete consequence. Do not reopen settled findings for a preferred
wording or file a prose-only Low when the required practice is already correct.
If the scoped checks find no defect, file nothing and proceed to finish;
there is no quota of findings or mandatory residual risk.

## Record and finish

Append each new finding once to Findings in the seven-field shape:

  F1 | Critical | Task ordering | T3 | open | description | recommended fix

The category is free text and the linter does not check it. `Task ordering`,
`Unnecessary scope`, and `Policy` are the named ones; keep to them where one
fits so a later pass can count like with like.

Use `-` for a plan-level finding and no pipes inside prose. Findings,
changelog entries made by `plan resolve`, and runtime stage metadata are the
only writes. Do not revise the plan or resolve your own new findings.

For a text-edit fix, identify the exact file and section or line, the target
text, and its replacement (or deletion). Never reproduce secrets or personal
data in a finding: use a safe locator and a redacted target in those cases.
For a repeated reopen, state precisely which part of that edit is still absent;
do not substitute another verification exercise for the original ask.

Then run:

1. `.claude/bin/plan finish review` — atomically records `reviewed:` and clears
   the active marker.
2. `.claude/bin/plan lint`.
3. `.claude/bin/plan recommend` and inspect its command.

After a revision review, name what the scoped pass did not inspect. If the
recommendation is not `/cs-revise`, print it and stop. If it is `/cs-revise`,
continue in this session: leave plan mode when the surface requires that before
edits, read the installed `cs-revise.md` beside this command (`.claude/commands/`
under Claude Code; `.agents/coldsession/commands/` under Codex), and follow it
completely with no arguments. Do not merely recommend Revise or wait for another
user command. Its resulting revision still requires Review in a new session.
