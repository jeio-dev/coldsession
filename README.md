# coldsession

Every step that judges the previous one runs cold.

A six-step planning loop for coding agents, packaged as ten slash commands
and one dependency-free script. The session that reviews a plan never held
the pen that wrote it, the phase file carries a linted task graph, and a
build session reads a computed list of files rather than a codebase.

    /define → /plan → /review → /revise → /approve → /build → /close

## Install

Clone into the project, run it, and it deletes itself.

```bash
cd ~/my-project
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.coldsession/install.sh
git add .claude templates && git commit -m "chore: coldsession"
```

**Windows (PowerShell):**

```powershell
cd $HOME\my-project
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.\.coldsession\install.ps1
git add .claude templates; git commit -m "chore: coldsession"
```

The clone never outlives the install, so nothing has to live outside the
project and there is no second copy to remember to update. Pass `--keep`
(`-Keep` under PowerShell) to leave it in place. Only `.coldsession` at the
root of the target is treated as disposable — a clone under another name, or a
checkout you keep somewhere else, is left alone and merely mentioned. Both
installers take the target directory as their first argument, defaulting to
the current one.

`install.ps1` mirrors `install.sh`: it copies the commands, the `plan` tool,
and the templates, and writes `.claude/settings.json` only if one doesn't
already exist. It needs `python3` (or `python`, or `py`) on `PATH`. The script
is BOM-less UTF-8 and ASCII-only, so it parses cleanly under Windows
PowerShell 5.1 as well as PowerShell 7+.

## Update

An install pins the tool's version into the project, so a fix to `plan` or
the commands doesn't reach an already-installed project on its own.
`update.sh` (`update.ps1` on Windows) re-copies just `.claude/commands/`,
`.claude/bin/plan`, and `.claude/bin/plan.cmd` from a fresh clone; it refuses
to run against a project with no existing install, and never touches
`templates/` or `.claude/settings.json` — those are yours once installed.

```bash
cd ~/my-project
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.coldsession/update.sh
git add .claude && git commit -m "chore: update coldsession"
```

Same `--keep`/`-Keep` and self-deleting clone as install. Prints the version
before and after, so `git diff .claude` isn't the only way to tell what
changed — `plan version` on its own does too.

```
.claude/commands/*.md    the ten commands
.claude/bin/plan         the graph and context tool
.claude/bin/plan.cmd     the same tool, entered from Windows
.claude/settings.json    opusplan routing + permission for the tool
templates/               PLAN.md, phase.md
docs/plans/              phase files land here
```

`plan` is an extension-less Python file with a shebang. POSIX shells and Git
Bash run it directly; PowerShell cannot run an extension-less file at all, and
does not apply `PATHEXT` to an explicit path, so a `.cmd` sitting next to it
isn't found either. `install.ps1` therefore points the commands it installs at
`.claude/bin/plan.cmd`, which works from PowerShell, cmd.exe, and Git Bash
alike. Both installers ship both files, so a repo installed on one platform
still runs on the other; a teammate on the other OS re-runs their own
installer, which repoints the commands and touches nothing else.

Installs per project, not globally, so the workflow version pins with the
code and a phase planned six months ago still reads the way it was planned.
Commit `.claude/` with the repo.

Needs `python3` and an agent that reads `.claude/commands/`.

## The loop

| Command | Session | Mode | What it does |
|---|---|---|---|
| `/define <idea>` | 1 | plan · opus | Idea → objective brief. Asks, doesn't guess. |
| `/groundwork` | 1 | normal · sonnet | Greenfield only. AGENTS.md, scaffold, commands that actually run. |
| `/plan` | 1 | write · sonnet | Brief → `PLAN.md` + a phase file with a task graph. |
| `/review` | 2, new | plan · opus | Independent skeptic. Severity-tagged findings. |
| `/revise` | 2 | write · sonnet | Resolve findings, write the changelog. |
| `/recheck` | 3, new | plan · opus | Rounds 2+. Reads the changelog, not the phase. |
| `/approve` | new | normal · sonnet | Evidence checklist. Issues no verdict. |
| `/build T2` | one per task | normal · sonnet · `--effort medium` | One task, verified, committed. |
| `/close` | new | normal · sonnet | Harvest corrections, audit, advance the pointer. |
| `/status` | anywhere | any | Four lines. Reads no source. |

A command supplies prompt text and nothing else. It does not start a session,
enter plan mode, or pick a model. `/review` typed into the session that wrote
the plan gives you a compromised review with correct wording, which is worse
than skipping it — it looks like a review.

Every command from `/plan` onward ends by printing `plan recommend`, so the
next step comes from the phase file rather than from you remembering the
order. `/define` and `/groundwork` recommend statically; nothing is on disk
yet to derive from.

`/approve` deliberately cannot approve. You set `status: approved` in the
phase file's frontmatter yourself. A model grading its own revision against
criteria it just satisfied passes itself every time.

**Stop condition.** If round three still produces a Critical, the phase is
too large or the objective is wrong. Split it and re-plan. A loop with no exit
is how a planning workflow becomes a way of avoiding the build. `plan lint`
warns at that point (`W05`) and `plan recommend` sends you to `/plan` instead
of `/revise`.

## Findings

A finding that only exists in the session that found it is gone, because that
session is meant to end. `/review` writes its findings into the phase file's
`## Findings` block, one per line, seven fields:

```
F1 | Critical | Task ordering | T3 | open | T3 reads the queue but does not depend on T2 | add T2 to T3 deps
F3 | Medium   | Unnecessary scope | T2 | accepted | types.ts duplicates the schema | drop it or import from T1
```

Same bargain as the task graph: a narrow shape the tool can parse, no pipes
inside the prose, and a malformed line fails loudly as `E12` rather than
disappearing. `/revise` closes each one with

```
plan resolve F1 resolved "T3 now depends on T2"
```

which flips the status and appends `rev 2 | F1 | resolved | T3 now depends on
T2` to the changelog in the same step, so the two can't disagree. `resolved`
means the plan changed; `accepted` means it didn't and here's why. The note
has to name a task ID or plan line — `/approve` fails a changelog entry that
just says "fixed", and `/recheck` reads the changelog rather than the phase,
so an entry that names nothing gives it nothing to check.

`reviewed:` in the frontmatter carries the rev of the last review pass.
Against `rev:`, it is what tells `/recheck` there is something new to look at
and what stops `/approve` from grading an unreviewed revision.

## The task graph

The phase file's frontmatter is machine-readable; the body is prose. Neither
duplicates the other, and `plan lint` fails if they drift.

```yaml
---
phase: 02-offline-sync
rev: 3
status: approved
reviewed: 3
workflow-rev: 1.1.0
tasks:
  T1: {deps: [], status: done, files: [src/db/schema.ts]}
  T2: {deps: [T1], status: pending, files: [src/sync/queue.ts, src/sync/types.ts]}
  T3: {deps: [T1], status: pending, files: [src/sync/worker.ts]}
  T4: {deps: [T2, T3], status: pending, files: [src/sync/index.ts]}
---

## T2 — write queue
Goal: ...
Acceptance Criteria: ...
Verify: `npm test -- queue` exits 0
```

`files` carries the most weight and gets written the most carelessly. It is
the contract a build session is bounded to: a missing entry stalls the build,
an over-broad one spends context you don't get back. The linter can only
check that it's non-empty, so `/review` checks it against the real codebase.

`Verify` is the other load-bearing field. Build cannot mark a task done
without running that command and showing its output, so a task whose Verify
line is "confirm it works" is a task Build can pass by asserting. `/review`
treats one as a High finding.

## plan

```
plan status              phase, counts, findings, what's runnable, what's next
plan recommend           one line: the next command to run, and why
plan lint                validate graph and findings; exit 1 on error
plan next [--parallel]   next runnable ids; --parallel groups by file overlap
plan brief T2            bounded read list + verify line for one task
plan done T2             mark done, refusing if a dependency isn't
plan block T2 "reason"   mark blocked and append to the phase log
plan findings [--open]   the finding list
plan resolve F1 STATE    close or reopen a finding, logging it to the changelog
plan bump                bump the phase rev, at the start of a revise pass
plan reviewed            record that this rev has had a review pass
```

`lint` catches unparseable task lines, unknown or cyclic dependencies, tasks
marked done ahead of their dependencies, empty `files` lists, missing
`Verify:` lines, graph entries with no body section, body sections with no
graph entry, malformed or duplicated findings, findings naming tasks that
don't exist, findings closed without a changelog entry, and an approved phase
with an open Critical or High. `/review`, `/recheck`, and `/approve` all run
it, so shape errors never consume a human review round.

`recommend` derives the next command from the file: unreviewed sends you to
`/review`, open findings to `/revise`, a revision newer than its last review
pass to `/recheck`, a clean reviewed rev to `/approve`, an approved phase to
`/build` with the first runnable id, a finished one to `/close`. It prints the
state that produced the answer, so a recommendation you disagree with is one
you can check rather than guess at.

The frontmatter parser is regex-based on a deliberately narrow one-line-per-
task shape rather than a real YAML parse, to stay stdlib-only. A malformed
write fails loudly as `E01` with the offending line quoted, rather than
silently mis-parsing.

## Context

`plan brief T2` prints a fixed read list: `AGENTS.md`, the phase file, the
files of every task T2 depends on transitively, then T2's own. Full closure,
not just direct deps — a file that only reaches T2 through T1→T3→T2 still
belongs in the brief.

```
task    T2   status pending
read    AGENTS.md
        docs/plans/02-offline-sync.md
        src/db/schema.ts
        src/sync/queue.ts
        src/sync/types.ts
        (nothing else; if you need a file that is not listed, stop and say so)
verify  `npm test -- queue` exits 0
handoff docs/plans/02-offline-sync.log.md  (read the last entry only)
```

Two things follow. A wrong `files` entry surfaces as a session that stops and
tells you, instead of one that quietly explores half the repo. And the prefix
is byte-identical across every build session in the phase, so everything
before the task's own files is a cache read rather than a fresh one.

Searching is not reading. To locate something, a session dispatches a subagent
and takes back the `file:line`, keeping grep output out of the context that
has to hold the task.

## Handoffs

Each build task appends at most ten lines to `docs/plans/NN-slug.log.md`:
decisions the plan didn't specify, gotchas, places the code differed from what
the plan assumed. Never a summary of the diff — git has that. The next session
reads the last entry, so nothing has to survive in a terminal you closed.

## Token levers, largest first

1. Bounded reads. A build session opens a listed set, not a codebase.
2. Fixed read order, so the cache prefix is reused instead of rebuilt.
3. `/recheck` instead of a second full `/review`.
4. Eight tasks per phase, capped, because every session re-reads the file.
5. `claude --effort medium` for build. A task that survived review doesn't
   need `high`, which is the default.
6. Search subagents, results only.
7. Exit sessions, never `/compact` — it reprocesses the whole conversation and
   then charges you to re-read the summary.

## Parallel builds

`plan next --parallel` partitions the runnable set by file overlap. Tasks in
one group share no files and can run in separate terminals at once; groups run
in sequence. Two sessions is usually the ceiling worth having, and on a plan
with a usage cap it may be zero — parallelism costs tokens in proportion to
how much you use it. Treat this as a scheduling readout first.

## Model routing

`.claude/settings.json` sets `opusplan`, so plan mode runs Opus and execution
runs Sonnet. One rule covers the workflow: reason in plan mode, exit plan mode
to write. Toggling back and forth re-reads the history uncached, so reason,
exit, write, stop.

A model chosen with `/model` is saved into `~/.claude/settings.json` and
quietly applies to every session after; `effortLevel` behaves the same way.
Clear both so the project setting and the launch flag win.

## When to skip this

| Gear | When |
|---|---|
| Direct | Reversible, one or two files, obvious answer. Just ask. |
| Short loop | `/plan` → `/review` → build, one session, nothing on disk. |
| Greenfield | `/define` → `/groundwork` → full loop. |
| Full loop | New surface, schema, auth, payments — anything expensive to unwind. |

The full loop costs four sessions before a line of code exists. That pays for
itself on a new surface area and is pure overhead on a copy change. Touching
data ownership, auth, or money puts you in the full loop regardless of how
small the diff looks.

## What v1.0.0 commits to

Semver applies to four things. Everything else is free to change in a patch.

1. **Command names.** `/build T2` keeps working.
2. **The `tasks:` frontmatter shape, and the `## Findings` line shape.** Phase
   files planned under 1.x stay readable by 1.x tooling. A file written before
   findings existed still lints and builds.
3. **`plan` subcommands and exit codes.** `lint` exits 1 on error; scripts can
   rely on it. Subcommands get added in a minor release, never removed in one.
4. **Install paths.** `.claude/commands/`, `.claude/bin/plan`, `templates/`.

Prompt wording inside a command is not part of the contract — it will change
whenever the model's behavior makes it worth changing.

Every project holds its own copy of the tool and its own phase files, so
there is no central migration. `plan lint` refuses a phase file whose major
`workflow-rev` differs from the tool's rather than mis-parsing it.

## Docs

`docs/universal-planning-workflow.html` is the reasoning behind each step —
why fresh sessions, why the human holds the approval, why the file list is the
field that matters. The command files are canonical; the document explains
them.

## License

MIT.
