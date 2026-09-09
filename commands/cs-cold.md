---
description: Run the next workflow step in a genuinely new session, spawned in Orca
argument-hint: [/cs-command]
---

Every step that judges the previous one runs cold. Without Orca that means
quitting this session and starting another by hand; with Orca it means opening
a second terminal in this same worktree, which is a stronger guarantee — a
separate process with its own session id and empty scrollback — and one
command instead of a context switch.

This command hands work over. It does not supervise the session it starts, and
it does not run the step itself.

## Resolve the CLI

Use `$ORCA_CLI_COMMAND` when it is set, `orca-dev` when `$ORCA_DEV_REPO_ROOT`
is set, `orca-ide` on Linux outside an Orca terminal, and `orca` otherwise.
Below, `ORCA` means the one you resolved. On Linux, bare `orca` outside an
Orca-managed terminal is the GNOME screen reader, so never fall through to it.

Run `ORCA status --json`. If the CLI is missing or the runtime is unreachable,
print exactly this and stop — do not try to start Orca, and do not run the step
here:

    Orca is not available. Exit this session and run <command> in a new one;
    the phase file carries everything it needs.

## Choose the command

With an argument, use it verbatim. With none, run `.claude/bin/plan recommend`
and take its command. Stop and print the output unchanged if it names no
runnable `/cs-` command — `(set status: approved)`, `(fix the linter first)`,
and `(nothing runnable)` are all answers for the human, not work to hand off.

Refuse to spawn `/cs-status`; it reads no source and belongs in this session.

## Check the placement

Run `ORCA worktree show --worktree active --json` and compare its path to the
repository root. If they differ, the new terminal would start outside the
project. Say so and stop rather than launching in the wrong directory.

## Choose the session shape

The project's `.claude/settings.json` sets `opusplan`, so plan mode already
runs Opus and execution runs Sonnet. Pass no `--model`: routing belongs to that
setting, and a flag here would silently outrank it and drift from it.

| Command | Launch |
|---|---|
| `/cs-define`, `/cs-review` | `claude --permission-mode plan` |
| `/cs-build` | `claude --effort medium` |
| `/cs-plan`, `/cs-revise`, `/cs-approve`, `/cs-close` | `claude` |

## Hand it over

    ORCA terminal create --worktree active --title '<command>' --command "<launch>" --json
    ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json
    ORCA terminal send --terminal <handle> --text '<command>' --enter --json

Read the handle from the create response and use only that one. Wait for
`tui-idle` before sending, or the prompt races startup and is lost. If the wait
times out, say so and leave the terminal alone — a started agent that never got
its prompt is recoverable by hand; a second send is not.

Quote `<command>` literally, with single quotes in both POSIX shells and
PowerShell, when you run these lines yourself. The Codex form of a command is
`$cs-review`, `$cs-build`, and so on (see below); inside a double-quoted
argument a shell expands `$cs` — usually unset — to nothing and leaves the
rest, so `"$cs-review"` arrives as `-review`. Single quotes keep the payload
literal on both surfaces.

Do not use `orca orchestration` here. A cold session is a handoff, and a
coordinator preamble would make it report back to this session — the opposite
of the independence the step exists to get.

## Report

Print three lines: the command handed off, the terminal handle, and that this
session is now done. Then stop. Do not read the new terminal's output, do not
wait for it, and do not do the step yourself.
