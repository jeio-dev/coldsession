---
description: Delegate read-only exploration to the configured scout (experimental)
argument-hint: <locate|trace|inventory> <target> [--include PATH]... [purpose]
---

Scout is experimental. It hands one read-only exploration request to an
external agent CLI and returns a report whose evidence the runtime has already
checked. It never edits the tree. A wrong call costs time, never a change.

Run `.claude/bin/plan scout status` first. If it exits non-zero, print its
line, explore natively, and stop following this file. Scout is off until a
human runs `.claude/bin/plan scout setup`; never run setup yourself, because
it accepts a data-sharing disclosure on the human's behalf.

## Run a request

Choose one kind and fill its parameters from `$ARGUMENTS`, or, when a workflow
command sent you here, from what you are about to explore:

- `locate symbol=NAME`: where NAME is defined and where its behavior lives.
- `trace from=A to=B`: how control or data flows from A to B.
- `inventory symbol=NAME`: every reference to NAME in scope.

If `$ARGUMENTS` already reads `KIND NAME=VALUE...`, use it as given. If no kind
fits or a parameter is missing, ask one question and stop. There is no free-form
question: the runtime renders a fixed template from these parameters.

Run:

```text
.claude/bin/plan scout run KIND NAME=VALUE... --purpose "<one short line>" [--include PATH]... [--exclude PATH]... [--known "<fact>"]...
```

- `--purpose` says why you need it, such as "about to change token refresh".
- `--include` narrows the scope to the smallest set of directories that can
  hold the answer; the default is the whole repository.
- `--known` passes facts you already established, so the scout skips them.

Where your harness can run a shell command in the background (Claude Code's
`run_in_background`), do so and keep working on anything that does not depend
on the answer. Otherwise run it in the foreground. The runtime enforces the
configured timeout either way; do not add your own retries.

During an active Build claim, the scout can cite only files in the task's read
set. The runtime enforces this, and it is not a way to reach outside the brief.

The command exits 0 with a report, or exits 1 with exactly one line:
`scout unavailable (<reason>); explore natively`. On that line, print it as
given and explore natively. Do not rerun the same request.

## Use the report

- Verified locations (`E1 file:lines`) are fact. The runtime matched each
  snippet against the file. Do not re-explore them.
- The answer, each `why`, and each trace step are working assumptions, not
  facts.
- Read every `read next` range yourself before editing anything it covers.
- For each `unknown`, explore natively or send one narrower request.
- A report is orientation only. Never cite it, or any path under
  `.coldsession-state/scout/`, as verification, review, or completion
  evidence. The runtime refuses it with E36.

When `$ARGUMENTS` invoked this command directly, end with a short summary: the
status, the verified locations, and the ranges to read next.
