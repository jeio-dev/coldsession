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

## Scout benchmark

`evals/scout.py` measures whether scout saves host tokens. Each scenario in
`evals/scenarios/scout/` pins a revision of this repository, optional exact
patches (an injected regression for the fix task), an exploration-heavy task,
the writable files, and grading code. Each run extracts that revision into a
new git repository, installs coldsession, commits, and starts Claude with the
same prompt and permissions. The prompt ends with the soft rule the workflow
commands carry: check `plan scout status` and follow it only when it exits 0.
The one treatment is whether `plan scout setup` ran, and with which model.
The native arm has scout off. Permissions are scoped rules on the command
line: `plan scout` commands and the writable files only. The isolated
configuration does not apply a fixture's `settings.json` permissions.

To use a gateway such as OpenRouter, set `ANTHROPIC_BASE_URL`,
`ANTHROPIC_AUTH_TOKEN`, an empty `ANTHROPIC_API_KEY`, and `ANTHROPIC_MODEL`.
The report records the endpoint and the model. The CLI's cost figure is its
own estimate, so the gateway's spending cap is the real limit.

```text
python evals/scout.py --prepare-only --accept-data-sharing --model gemini-3.8-flash-low
python evals/scout.py --live --accept-data-sharing --budget-usd 20 --repeats 2 \
    --model gemini-3.8-flash-low --model gemini-3.8-flash-high --output evals/results/scout-comparison.json
python evals/scout.py --summarize evals/results/scout-comparison.json
```

`--accept-data-sharing` is you accepting the scout disclosure for the fixture
projects. Their content goes to the scout provider. The Claude budget is
split equally across runs. Provider usage is not measured and is governed by
the provider's own limits. Arm order rotates between repeats.

Each run records the following:

- host tokens and cost reported by the harness (unknown stays unknown);
- the scout counters: runs, accepted, rejected by reason, fallbacks, cache
  hits, timeouts, and tree changes;
- the scout commands the host ran;
- wall time, check results, and changed files, including any outside the
  writable scope.

The rejection rate is rejected reports divided by all reports the provider
returned. Timeouts and provider failures are fallbacks, not rejections. An arm
passes when it meets all three conditions:

- its paired median host tokens are at least 10% below native;
- its rejection rate is under 20%;
- its correctness is no lower than native.

The keep verdict needs at least one passing arm. The default model is the
fastest passing arm. An arm with unknown tokens, or with no scout report at
all, gives `insufficient evidence`, not a pass. Record the decision (keep,
narrow, or remove; the default model; the experimental label) beside the
retained report.

Codex gap: `lib.run_claude` drives only the Claude CLI, so there is no Codex
arm. Scout reaches Codex through the same runtime and `$cs-scout` adapter,
but its savings there are unmeasured.

The existing prompt fixtures cover persisted review findings, human-only
approval, and durable phase-boundary context. `tests/test_evals.py` checks their
graders, isolation, and redaction without spending tokens. Live runs are not
part of CI. Require deterministic release checks and inspect live comparison
evidence before claiming quality or efficiency improvements.
