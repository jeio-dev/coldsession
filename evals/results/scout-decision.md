# Scout decision (#22)

Date: 2026-09-19. Decision: **narrow**. Scout stays experimental and opt-in.

## Setup

- **Report:** `scout-comparison.json`, with 48 runs. Every run is kept,
  failures included.
- **Smoke test:** `scout-smoke.json`, one scenario, run before the sweep.
- **Host:** Claude Code with `anthropic/claude-sonnet-5`, through OpenRouter.
  Small calls went to `anthropic/claude-haiku-4.5`.
- **Scout provider:** `agy` 1.2.7 on Windows, default timeout 180 s.
- **Scenarios:** the six in `evals/scenarios/scout/`, pinned to v3.4.0
  (`a205002`). Each ran twice per arm, with arm order rotated.
- **Arms:** native (scout off), `gemini-3.8-flash-low`,
  `gemini-3.8-flash-high`, and `claude-sonnet-4-6`.
- **Budget:** $12 total, split to about $0.25 per run. About $8.85 was spent,
  by the Claude CLI's own estimate. Scout provider usage is not measured.
- **No Codex arm:** the runner drives only the Claude CLI.

## Result

```text
python evals/scout.py --summarize evals/results/scout-comparison.json
```

| Arm | Correct | Median host tokens | vs native | Rejection rate | Median time |
|---|---|---|---|---|---|
| native | 10/12 | 400k | – | – | 48 s |
| `gemini-3.8-flash-low` | 8/12 | 447k | +11% | 40% (4 of 10) | 114 s |
| `gemini-3.8-flash-high` | 7/12 | 493k | +17% | 9% (1 of 11) | 158 s |
| `claude-sonnet-4-6` | 9/12 | 489k | +20% | 100% (10 of 10) | 91 s |

- **Rejection reasons:** `gemini-3.8-flash-low` had 3 `invalid_shape` and
  1 `uncited_hit`; `gemini-3.8-flash-high` had 1 `invalid_shape`;
  `claude-sonnet-4-6` had 10 `invalid_shape`.
- **No arm meets the keep rule:** at least 10% fewer host tokens, rejection
  below 20%, and correctness no lower than native.
- **Even accepted reports saved nothing.** In the 14 runs whose report was
  accepted, host tokens were within about 1% of the same scenario's native
  median.
  - The host still reads the `read next` ranges itself, as `/cs-scout`
    instructs.
  - These sessions use 300–700k host tokens, mostly fixed context, so
    replacing a few file reads does not move the total.
- **Scout makes the host 2–3 times slower,** because the host waits for the
  provider.

## Caveats

- **Budget cutoffs:** the per-run budget was too small for the larger tasks.
  11 runs across all arms hit `error_max_budget_usd` before writing an answer.
  Excluding those runs does not change the direction of any arm's result.
- **Possibly ambiguous question:** in `issue-adoption`, part (b) reads "the
  issue body hash recorded in a phase". Two scout runs answered `source_issue`
  (which reads a stored hash) instead of `issue_body_sha256`. The wording
  should be tightened before this scenario is reused. Native answered
  correctly both times.
- **Write denied at a wrong path:** one `installed-claude-hooks` run
  (`gemini-3.8-flash-high`, repeat 2) found the correct answer. Its write went
  to a wrong absolute path (`\tmp\...`), was denied, and counts as incorrect.
- **Narrow coverage:** one host model, one small repository, and Windows only.
  Larger codebases, where exploration is a larger share of the session, are
  untested.

## Decision

- **Narrow, not remove.** Stop sending the workflow commands to scout
  automatically. The data shows the soft rule costs time and saves no host
  tokens. Keep `/cs-scout` as an explicit, opt-in command.
- **Default model: `gemini-3.8-flash-high`.** It is the only model that passed
  validation reliably (9% rejected). The faster `gemini-3.8-flash-low` rejects
  40%.
- **Experimental label: stays.** No arm showed a saving.
- **Ongoing signal:** the `plan doctor` scout counters from real use, as
  planned in #17.

## Follow-ups

Each is outside #22, which excludes scout changes.

1. Remove the scout line from `/cs-define`, `/cs-plan`, and `/cs-issue`.
   Set the default model.
2. Investigate why `claude-sonnet-4-6` through `agy` never returns a
   schema-valid report.
3. Re-measure on a larger repository, with a per-run budget of at least
   $0.60, before any claim that scout saves tokens.
