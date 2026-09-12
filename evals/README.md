# Behavioral evaluations

Deterministic checks run without a model:

```text
python -m unittest discover -s tests -q
```

Live evaluation is explicitly opt-in and budgeted. Use a disposable environment
with the Claude CLI and an explicitly supplied `ANTHROPIC_API_KEY`. The runner
creates its own Claude configuration directory, uses project settings only,
isolates MCP configuration, and strips inherited plugins, session identities,
worker assignments, and orchestration variables. It preserves native permission
checks; permission denials and failed runs count as outcomes. It never enables
permission bypass or automatically installs plugins.

```text
python evals/run.py --live --max-budget-usd 2.00 review-writes-findings
python evals/compare.py evals/scenarios/refund-total.json --baseline /path/to/v2.5.0 --live --budget-usd 6.00 --output comparison.json
```

The comparison divides the total budget equally across direct harness use,
the unchanged baseline release, and the improved workflow. Each arm starts
with identical application source, task, acceptance criteria, and scenario
permissions. Workflow arms use synthetic already human-approved fixture state;
this evaluates implementation behavior, not the complete planning loop. The
baseline path must be a known unchanged release checkout. No installer or
production phase is silently approved by this fixture setup.

Scenario JSON declares source files, writable scope, verification commands,
and external grading code. The grader runs outside the agent's editable test
files after each session. Add scenarios for review false positives, scope
recovery, regressions, and larger tasks before drawing broad conclusions.

The report retains all runs, including failures, measured harness usage/cost
when provided, elapsed time, permission denials, timeout and truncation flags,
correctness checks, regression count, changed files, and changes outside the
expected scope. Out-of-scope file changes are a proxy for unnecessary work;
within-file unnecessary edits and false findings require independent human
adjudication. Record that adjudication alongside the report. Headless runs
have zero human interventions; denied operations are reported separately.

Output and retained traces are bounded, and likely credentials are filtered
before persistence. A truncated trace cannot establish that an action never
happened. Redaction is heuristic, so do not put credentials in fixture content.
Actual token counts come from harness usage; missing usage remains unknown.
No prompt-cache guarantee or quality/token saving claim follows from an estimate.

The existing prompt fixtures cover persisted review findings, human-only
approval, and durable phase-boundary context. `tests/test_evals.py` checks their
graders, isolation, and redaction without spending tokens. Live runs are not
part of CI. Require deterministic release checks and inspect live comparison
evidence before claiming quality or efficiency improvements.
