---
description: Implement one approved task, verify it, commit, stop
argument-hint: [task-id] [--resume]
---

Parse `$ARGUMENTS` as one task ID plus optional `--resume`. If the ID is blank,
run `.claude/bin/plan recommend` and stop.

Run `.claude/bin/plan start <task-id> [--resume]` first and inspect only its
output. If it refuses, print that output and stop before reading files. A task
already `in_progress` continues only with explicit `--resume`; done, blocked,
unapproved, and dependency-blocked tasks cannot start.

Then run `.claude/bin/plan brief <task-id>`.

## Reading

Read exactly the files the brief lists, in order, beginning with AGENTS.md.
Nothing else. If a required file is absent, stop and name it; that is a plan
finding, not permission to expand context. Locate symbols with search and keep
only file:line results.

## Doing

Restate the acceptance criteria and Verify line, then implement only this task.
Do not change architecture, the plan, or another task.

A task is done only after running its Verify command and showing the output.
For a named visual check, perform the exact action and report the visible result.

On success:

1. Append at most ten lines to the phase log: `## T(n)` and only decisions,
   gotchas, or mismatches the next session cannot derive. Otherwise write
   `nothing to carry`.
2. `.claude/bin/plan done <task-id>` — it accepts only `in_progress` tasks.
3. Commit task changes, phase state, and log together with the task ID in the
   message.
4. Print `.claude/bin/plan recommend` and stop.

On a blocker, run `plan block <task-id> "reason"`, add the next open High Risk
finding with its concrete unblock action, print `plan recommend`, and stop.
