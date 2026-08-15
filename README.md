# coldsession

Every step that judges the previous one runs cold.

A six-step planning loop for Claude Code and Codex, packaged as ten Claude
slash commands, ten matching Codex skills, and one dependency-free script.
The session that reviews a plan never held the pen that wrote it, the phase
file carries a linted task graph, and a build session reads a computed list
of files rather than a codebase.

    /cs-define → /cs-plan → /cs-review → /cs-revise → /cs-approve → /cs-build → /cs-close → /cs-plan …

## Install

Clone into the project, run the installer, choose Claude Code, Codex, or both,
and the temporary clone deletes itself.

```bash
cd ~/my-project
git clone --depth 1 --branch v2.0.0 https://github.com/jeio-dev/coldsession.git .coldsession
.coldsession/install.sh --agent both
git add .claude .agents templates && git commit -m "chore: coldsession"
```

**Windows (PowerShell):**

```powershell
cd $HOME\my-project
git clone --depth 1 --branch v2.0.0 https://github.com/jeio-dev/coldsession.git .coldsession
.\.coldsession\install.ps1 -Agent both
git add .claude .agents templates; git commit -m "chore: coldsession"
```

`--branch v2.0.0` pins the clone to a tagged release rather than whatever's
on `main`, so following this README always gets a tested version; bump it to
the latest tag from the [releases page](https://github.com/jeio-dev/coldsession/tags)
if this copy of the README is older than the repo. The clone never outlives
the install, so nothing has to live outside the project and there is no
second copy to remember to update. Pass `--keep`
(`-Keep` under PowerShell) to leave it in place. Only `.coldsession` at the
root of the target is treated as disposable — a clone under another name, or a
checkout you keep somewhere else, is left alone and merely mentioned. Both
installers take the target directory as their first argument, defaulting to
the current one.

Omit the agent option for an interactive `Claude Code / Codex / Both` prompt.
Automation must pass it explicitly:

```text
./install.sh [target-dir] [--agent claude|codex|both] [--keep]
.\install.ps1 [[-Target] <dir>] [-Agent claude|codex|both] [-Keep]
```

The selection is authoritative. Re-running with `codex` removes only known
coldsession-managed Claude commands and runtime files; `claude` does the
inverse; `both` installs both surfaces. Other commands, skills, phase files,
and modified settings are left alone.

`install.ps1` mirrors `install.sh`. It needs Python on `PATH` and checks
`python3`, `python`, then `py`. The script is BOM-less UTF-8 and ASCII-only,
so it parses cleanly under Windows PowerShell 5.1 as well as PowerShell 7+.

## Update

An install pins the tool's version into the project. To update, clone the new
release and run `install.sh` or `install.ps1` again with the intended agent
selection. The installer detects an existing coldsession runtime, reports the
old and new versions, migrates managed 1.x names, and preserves templates and
phase files.

```bash
cd ~/my-project
git clone --depth 1 --branch v2.0.0 https://github.com/jeio-dev/coldsession.git .coldsession
.coldsession/install.sh --agent both
git add .claude .agents && git commit -m "chore: update coldsession"
```

```
.claude/commands/cs-*.md             Claude Code commands
.claude/bin/plan{,.cmd}              Claude runtime (when selected)
.claude/settings.json                Claude routing + permissions
.agents/skills/cs-*                  Codex skill adapters
.agents/coldsession/commands/cs-*.md Codex command copies
.agents/coldsession/bin/plan{,.cmd}  Codex runtime (when selected)
templates/                            PLAN.md, phase.md
docs/plans/                           phase files land here
```

`plan` is an extension-less Python file with a shebang. POSIX shells and Git
Bash run it directly; PowerShell cannot run an extension-less file at all, and
does not apply `PATHEXT` to an explicit path, so a `.cmd` sitting next to it
isn't found either. `install.ps1` therefore points each selected surface at
its adjacent `plan.cmd`, which works from PowerShell, cmd.exe, and Git Bash.
Both installers ship both runtime files, so a teammate on another OS can
re-run the installer with the same agent selection.

Installs per project, not globally, so the workflow version pins with the
code and a phase planned six months ago still reads the way it was planned.
Commit the selected `.claude/` and/or `.agents/` surface with the repo.

Needs `python3` and either Claude Code or Codex.
Launch either agent from the repository root; the installed command paths and
`PLAN.md` are root-relative. Codex skills discovered from a nested working
directory resolve those paths back to the repository root before running.

### Agent syntax

Claude Code invokes `/cs-define` and `/cs-build T2`. Codex invokes the matching
repository skills as `$cs-define` and `$cs-build T2`, or selects them through
`/skills`. Codex does not expose repository skills as arbitrary slash commands,
so the product-specific sigil differs while the `cs-*` stem and arguments are
identical.

The files in `commands/` are canonical. The installer copies them to Claude
and/or `.agents/coldsession/commands`, patching only the runtime path. Codex
skills remain small adapters for invocation arguments and next-step display.

## The loop

| Command | Session | Mode | What it does |
|---|---|---|---|
| `/cs-define <idea>` | 1 | plan · opus | Idea → objective brief. Asks, doesn't guess. |
| `/cs-groundwork` | 1 | normal · sonnet | Greenfield only. AGENTS.md, scaffold, commands that actually run. |
| `/cs-plan` | 1 | write · sonnet | Brief → `PLAN.md` + a phase file with a task graph. |
| `/cs-review` | 2, new | plan · opus | Independent skeptic. Severity-tagged findings. |
| `/cs-revise` | 2 | write · sonnet | Resolve findings, write the changelog. |
| `/cs-recheck` | 3, new | plan · opus | Rounds 2+. Reads the changelog, not the phase. |
| `/cs-approve` | new | normal · sonnet | Evidence checklist. Issues no verdict. |
| `/cs-build T2` | one per task | normal · sonnet · `--effort medium` | One task, verified, committed. |
| `/cs-close` | new | normal · sonnet | Harvest corrections, audit, close the phase. |
| `/cs-status` | anywhere | any | Four lines. Reads no source. |

A command or skill supplies prompt text and nothing else. It does not start a
session, enter plan mode, or pick a model. `/cs-review` (or `$cs-review`)
invoked in the session that wrote the plan gives you a
compromised review with correct wording, which is worse than skipping it — it
looks like a review.

Every command from `/cs-plan` onward ends by printing `plan recommend`, so the
next step comes from the phase file rather than from you remembering the
order. `/cs-define` and `/cs-groundwork` recommend statically; nothing is on disk
yet to derive from.

`/cs-approve` deliberately cannot approve. You set `status: approved` in the
phase file's frontmatter yourself. A model grading its own revision against
criteria it just satisfied passes itself every time.

**Stop condition.** If round three still produces a Critical, the phase is
too large or the objective is wrong. Split it and re-plan. A loop with no exit
is how a planning workflow becomes a way of avoiding the build. `plan lint`
warns at that point (`W05`) and `plan recommend` sends you to `/cs-plan`
instead of `/cs-revise`.

## Findings

A finding that only exists in the session that found it is gone, because that
session is meant to end. `/cs-review` writes its findings into the phase file's
`## Findings` block, one per line, seven fields:

```
F1 | Critical | Task ordering | T3 | open | T3 reads the queue but does not depend on T2 | add T2 to T3 deps
F3 | Medium   | Unnecessary scope | T2 | accepted | types.ts duplicates the schema | drop it or import from T1
```

Same bargain as the task graph: a narrow shape the tool can parse, no pipes
inside the prose, and a malformed line fails loudly as `E12` rather than
disappearing. `/cs-revise` closes each one with

```
plan resolve F1 resolved "T3 now depends on T2"
```

which flips the status and appends `rev 2 | F1 | resolved | T3 now depends on
T2` to the changelog in the same step, so the two can't disagree. `resolved`
means the plan changed; `accepted` means it didn't and here's why. The note
has to name a task ID or plan line — `/cs-approve` fails a changelog entry that
just says "fixed", and `/cs-recheck` reads the changelog rather than the phase,
so an entry that names nothing gives it nothing to check.

`reviewed:` in the frontmatter carries the rev of the last review pass.
Against `rev:`, it is what tells `/cs-recheck` there is something new to look
at and what stops `/cs-approve` from grading an unreviewed revision.

## The task graph

The phase file's frontmatter is machine-readable; the body is prose. Neither
duplicates the other, and `plan lint` fails if they drift.

```yaml
---
phase: 02-offline-sync
rev: 3
status: approved
reviewed: 3
workflow-rev: 1.3.0
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
check that it's non-empty, so `/cs-review` checks it against the real codebase.

`Verify` is the other load-bearing field. Build cannot mark a task done
without running that command and showing its output, so a task whose Verify
line is "confirm it works" is a task Build can pass by asserting. `/cs-review`
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
don't exist, findings closed without a changelog entry, and an approved or
closed phase with an open Critical or High. `/cs-review`, `/cs-recheck`, and
`/cs-approve` all run
it, so shape errors never consume a human review round.

`recommend` derives the next command from the file: unreviewed sends you to
`/cs-review`, open findings to `/cs-revise`, a revision newer than its last
review pass to `/cs-recheck`, a clean reviewed rev to `/cs-approve`, an
approved phase to `/cs-build` with the first runnable id, a finished one to
`/cs-close`, and a closed one to `/cs-plan` for the phase after it. It prints
the state that produced the
answer, so a recommendation you disagree with is one you can check rather than
guess at.

## The phase boundary

`/cs-close` ticks the phase in PLAN.md and marks the phase file `status: closed`.
It does not touch `current:`. Moving the pointer is `/cs-plan`'s job, in the same
edit that writes the new phase file, because a `current:` naming a file that
doesn't exist yet is a pointer every `plan` subcommand refuses to read — the
one moment you'd most want to ask the tool what to do next.

So the loop closes at `/cs-plan`, not `/cs-define`. `/cs-define` is a whole-product
brief: it runs once, before Phase 01, and produces something no file on disk
holds. Phase 02 has no product scope left to settle — `/cs-plan` opens in a new
session with no brief, reads the PLAN.md line, the phase you just closed and
its log, and AGENTS.md, then asks you what a one-line phase name can't say.

    /cs-plan → /cs-review → /cs-revise → /cs-approve → /cs-build → /cs-close → /cs-plan …

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
3. `/cs-recheck` instead of a second full `/cs-review`.
4. Eight tasks per phase, capped, because every session re-reads the file.
5. Moderate reasoning effort for build. In Claude Code that is
   `claude --effort medium`; in Codex, use the equivalent session setting.
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

Those settings are Claude-specific. The installer does not overwrite Codex
user or project model settings; Codex skills run with the model, reasoning
effort, and collaboration mode of the active Codex session.

## When to skip this

| Gear | When |
|---|---|
| Direct | Reversible, one or two files, obvious answer. Just ask. |
| Short loop | `/cs-plan` → `/cs-review` → build, one session, nothing on disk. |
| Greenfield | `/cs-define` → `/cs-groundwork` → full loop. |
| Full loop | New surface, schema, auth, payments — anything expensive to unwind. |

The full loop costs four sessions before a line of code exists. That pays for
itself on a new surface area and is pure overhead on a copy change. Touching
data ownership, auth, or money puts you in the full loop regardless of how
small the diff looks.

## Compatibility

Semver applies to four things. Everything else is free to change in a patch.

1. **Entry-point names.** In 2.x, Claude's `/cs-build T2` and Codex's
   `$cs-build T2` keep working.
2. **The `tasks:` frontmatter shape, and the `## Findings` line shape.** Phase
   files using the 1.x format remain readable by the 2.x tool. A file written
   before findings existed still lints and builds.
3. **`plan` subcommands and exit codes.** `lint` exits 1 on error; scripts can
   rely on it. Subcommands get added in a minor release, never removed in one.
4. **Install paths.** `.claude/commands/cs-*`, `.claude/bin/plan`,
   `.agents/skills/cs-*`, `.agents/coldsession/`, and `templates/`.

Prompt wording inside a command is not part of the contract — it will change
whenever the model's behavior makes it worth changing.

The tool release and phase format are versioned separately: `plan version`
prints the 2.x release, while new phase templates keep `workflow-rev: 1.3.0`.
`plan lint` compares that field with the supported format version, so updating
the installer does not invalidate an existing 1.x phase.

## Docs

`docs/universal-planning-workflow.html` is the reasoning behind each step —
why fresh sessions, why the human holds the approval, why the file list is the
field that matters. The command files are canonical; the document explains
them.

## License

MIT.
