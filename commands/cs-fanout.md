---
description: Build one file-disjoint group of approved tasks in supervised parallel sessions
argument-hint: [--max N]
---

`plan next --parallel` already partitions the runnable tasks into groups that
share no files. A group is therefore safe to build at once; until now it was
printed and the terminals were opened by hand, which caps the useful width at
about two. This command dispatches the group instead, and supervises it.

You are the coordinator. You do not build any task yourself.

## Resolve the CLI and check the preconditions

Use `$ORCA_CLI_COMMAND` when set, `orca-dev` when `$ORCA_DEV_REPO_ROOT` is set,
`orca-ide` on Linux outside an Orca terminal, and `orca` otherwise. Below,
`ORCA` means the one you resolved. Never fall through to bare `orca` on Linux
outside an Orca terminal; there it is the GNOME screen reader.

Run `ORCA status --json`. If the CLI is missing or the runtime is unreachable,
say so, print `.claude/bin/plan next --parallel`, and stop — the groups are
still useful as a readout, and the user can open the sessions by hand.

Orchestration is behind Settings → Experimental in Orca. If a command reports
it is unavailable, say exactly that and stop; it is a switch only the user can
throw.

If this session is itself a dispatched worker, `worker-start` refuses with
`nested_worker_depth_exceeded`. Report it and stop rather than routing around
it: a worker that fans out again is a coordinator nobody is watching.

## Choose the group

Run `.claude/bin/plan status` and `.claude/bin/plan next --parallel`.

Stop and print the output unchanged unless the phase is `approved` and at least
one group is runnable. Take the **first** group only; later groups overlap it
on files and must run after it. With `--max N`, take the first N ids of that
group and leave the rest for the next run.

A group of one is not worth a coordinator. Say so and recommend
`/cs-build <id>` in this session instead.

## Dispatch

    ORCA orchestration run-create --objective "<phase>: <ids>" --json
    ORCA orchestration task-create --spec '<spec, below>' --json      # once per id
    ORCA orchestration worker-start --task <task_id> --worktree current \
        --agent claude --model sonnet --effort medium --json          # once per id

Create every task first, then start every worker, then wait once. Starting and
waiting one at a time serialises the thing you came here to parallelise.

`--worktree current` is deliberate: the group shares no files by construction
and every task belongs to the branch being built, so a fresh agent terminal in
this worktree is the right isolation. Do not create a worktree per task.

`--model sonnet --effort medium` is the build row of the workflow's model
routing, made explicit because a worker terminal does not inherit this
session's settings.

Each task's spec is the build command plus the one thing a worker cannot infer:

    Run /cs-build <id> and follow it exactly, including its bounded read list.
    You are a supervised worker. Where the command tells you to exit the
    session, send worker_done instead and stop. If the brief is wrong or a
    file it omits is genuinely needed, do not widen your reads: use
    `orca orchestration ask` and wait for the answer.

Quote that spec literally with single quotes when you run `task-create`
yourself, on both POSIX shells and PowerShell. The Codex form of the build
command is `$cs-build <id>` (see the adapter), and inside a double-quoted
argument a shell expands `$cs` — usually unset — to nothing, so
`"$cs-build 3"` arrives as `-build 3`. Single quotes keep it literal.

Read each worker's dispatch id from its `worker-start` receipt. A receipt that
is not `ready` exits non-zero — report its `stage` and `effects` and do not
silently retry.

## Supervise

    ORCA orchestration check --wait --types worker_done,escalation,question \
        --timeout-ms 900000 --json

Parse stdout only. While `--wait` blocks it also writes keepalive lines to
stderr, and merging the streams breaks the parse.

Process every message in the batch before acknowledging it:

- `question` — answer it yourself only if the phase file already settles it.
  Otherwise put it to the user and wait. Reply with
  `ORCA orchestration reply --id <msg_id> --body "<answer>" --json`.
- `worker_done` — record the outcome, then
  `ORCA orchestration worker-release --dispatch <dispatch_id> --json`.
- `escalation` — surface it to the user with the worker's own words. Do not
  take over the task.

Then acknowledge and keep waiting until every dispatch has settled:

    ORCA orchestration check --ack <delivery_id> --wait \
        --types worker_done,escalation,question --timeout-ms 900000 --json

A timeout or an empty batch is a checkpoint, not a failure. Build tasks run for
tens of minutes, and heartbeats and terminal output mean alive, not finished.
Do not stop, release, or restart a worker that has not reported.

## Close out

Run `.claude/bin/plan status` and `.claude/bin/plan lint`.

A worker reporting `--outcome failed` has already marked its task failed; leave
the phase alone and report it. Do not mark a task done on a worker's behalf:
`/cs-build` runs `plan done` itself, and a task still `in_progress` after its
worker settled means the build did not finish, which is a fact the user needs
rather than one to paper over.

Print, in order: each task id with its outcome, anything a worker asked or
escalated, and `.claude/bin/plan recommend`. If more groups remain, say so and
name this command again.
