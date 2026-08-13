# Changelog

Format version and release version are the same number. A phase file records
the version it was planned under as `workflow-rev`, and `plan lint` refuses a
file whose major version differs from the tool's.

## [v1.1.1]

### The installer disposes of itself

Install used to ask for a clone somewhere outside the project — `~/src` in the
README — which left a second copy of the workflow on disk with nothing to keep
it current. The clone now goes inside the project and the installer removes it
as its last act:

    cd ~/my-project
    git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
    .coldsession/install.sh

Only `.coldsession` at the root of the target is treated as disposable. A
checkout that lives elsewhere, or a clone under another name, is left alone;
`--keep` (`-Keep` under PowerShell) skips the cleanup either way. `install.sh`
`exec`s the removal so the shell is replaced before the script it is reading
goes away, and `install.ps1` sets the working directory out of the clone first
and passes `-Force`, which clears the read-only bit git leaves on its objects.

## [1.1.0] — 2026-08-13

Findings became a file rather than a transcript, and the tool now says what to
run next.

### Findings on disk

Before this release `/review` printed its findings into a session that then
ended. `/revise` and `/recheck` had nothing to point at but whatever survived
in the terminal, which is the one thing a cold-session workflow guarantees is
gone. Findings now live in the phase file's `## Findings` block, one per line,
in a seven-field shape the tool parses:

    F1 | Critical | Task ordering | T3 | open | description | recommended fix

- `/review` writes them and runs `plan reviewed`. It exits plan mode to do it;
  that block and the `reviewed:` field are its only writes.
- `/revise` runs `plan bump` first, then closes each one with
  `plan resolve F1 resolved "T3 now depends on T2"`, which flips the status
  and writes the changelog entry in one step. A note that names no task ID or
  plan line is refused.
- `/recheck` reads `plan findings` and the changelog rather than the phase,
  and reopens what does not hold up with `plan resolve F2 open "..."`.

### A next step the tool computes

`plan recommend` derives the next command from the phase file, and every
command from `/plan` onward ends by printing it. `/define` and `/groundwork`
recommend statically, since nothing is on disk yet to derive from.

The recommendation reads `reviewed:` against `rev:`: unreviewed sends you to
`/review`, open findings to `/revise`, a revision newer than its last review
pass to `/recheck`, a clean reviewed rev to `/approve`, an approved phase to
`/build` with the first runnable id, and a finished one to `/close`. At rev 3
with an open Critical it recommends splitting the phase, which is the stop
condition the README already documented and nothing enforced.

### New in `plan`

- `plan recommend`, `plan findings [--open]`, `plan resolve F1 STATE "note"`,
  `plan bump`, `plan reviewed`.
- `plan status` gained a findings count and the `next` line.
- `plan brief` prints `NOT APPROVED` when the phase is not approved, so a
  `/build` typed too early stops before it reads anything.
- New lint rules: `E12` unparseable finding line, `E13` duplicate finding id,
  `E14` finding naming a task not in the phase, `E15` approved phase with an
  open Critical or High, `W04` finding closed with no changelog entry, `W05`
  the rev-3 stop condition.
- Fixed: body sections were only opened by a `## T(n)` heading, so everything
  under `## Findings` was parsed as part of the last task. A `Verify:` line in
  a finding description could satisfy `E08` for the wrong task.
- `plan version` no longer requires a PLAN.md to answer.
- Tool output is ASCII again; the two em-dashes in `plan brief` mangled on a
  cp1252 console, the same failure the 1.0.2 install fix was about.

### Windows

The commands called `.claude/bin/plan` as a bare path, which only ever worked
from a POSIX shell. `plan` is extension-less with a shebang: Git Bash runs it,
PowerShell refuses with "Cannot run a document in the middle of a pipeline",
and PowerShell does not apply `PATHEXT` to an explicit path, so dropping a
`.cmd` beside it is not enough on its own.

- Added `bin/plan.cmd`, which resolves `python3`/`python`/`py` and forwards
  arguments and exit codes. It runs from PowerShell, cmd.exe, and Git Bash.
  The `exit /b` is kept out of the parenthesised block on purpose:
  `%ERRORLEVEL%` expands at parse time inside one, which silently turned
  `plan lint`'s exit 1 into exit 0.
- `install.ps1` installs both entry points and repoints the commands it copies
  at `plan.cmd`, with a negative lookahead so re-running it cannot produce
  `plan.cmd.cmd`. `install.sh` installs both too and leaves the commands on
  the POSIX path, so a repo installed on either platform still runs on the
  other after its own installer is run.
- `plan` now reads files as `utf-8-sig`. Windows PowerShell writes a UTF-8 BOM
  by default, and a BOM ahead of the opening `---` meant `split_frontmatter`
  found no frontmatter at all, so a phase file written by `Set-Content
  -Encoding UTF8` read as having no tasks. Files are still written without
  one, so a BOM'd file is normalised the first time the tool writes it.
- Fixed in `install.ps1`: it never created `templates/`, so the template copy
  failed on any fresh project. `install.sh` had always created it.
- `install.ps1` writes `settings.json` without a BOM, and allows the
  `plan.cmd` path.
- Added `.gitattributes` pinning `*.cmd` and `*.ps1` to CRLF and `bin/plan`
  and `*.sh` to LF. A CRLF after `#!/usr/bin/env python3` sends the kernel
  looking for an interpreter named `python3\r`.

### Compatibility

`workflow-rev` is now 1.1.0. Phase files written under 1.0.x still lint and
build: no `## Findings` block means no findings, and a missing `reviewed:`
field reads as never reviewed, which starts the loop at `/review`. The fields
are added in place the first time `plan reviewed` or `plan resolve` runs. The
task graph shape, the command names, the subcommand exit codes, and the
install paths are unchanged.

`.claude/bin/plan.cmd` is a new install path, not a moved one. A project that
upgrades by re-running `install.sh` keeps calling `.claude/bin/plan` and needs
no other change.

## [1.0.2] — 2026-08-07

Bugfix release for `install.ps1` on Windows PowerShell.

- Fixed a parse error on the final line: `<your idea>` inside a double-quoted
  string, where `<`/`>` are reserved operators. Switched to a single-quoted
  literal.
- Fixed a second, hidden parse error: an em-dash in a UTF-8 file without BOM.
  Windows PowerShell 5.1 decodes BOM-less files as ANSI, misreading the
  em-dash's bytes as `”` (U+201D), which prematurely closed the string and
  cascaded into a "Missing closing '}'" error. Replaced the em-dash with an
  ASCII hyphen.
- Both `install.ps1` copies (repo and Desktop) verified clean with the
  PowerShell AST parser.

## [1.0.1] — 2026-08-07

Audit release. No command prompt content changed.

- Reviewed all ten `commands/*.md` files against Anthropic's July 2026
  guidance on Claude 5-generation context engineering (rigid rules replaced
  with judgment-based instructions where the rule was compensating for
  weaker model judgment). Found nothing to change: this tool has no
  docstring/comment-style rules, and its hard "Never/Do not" rules are either
  mechanical parser requirements, self-grading/corner-cutting guardrails, or
  context-budget discipline — none are model-capability crutches.
- `bin/plan` and `install.sh` marked executable (file mode only, no content
  change).

## [1.0.0] — 2026-08-07

First release.

### The loop
- Ten commands: `/define`, `/groundwork`, `/plan`, `/review`, `/revise`,
  `/recheck`, `/approve`, `/build`, `/close`, `/status`.
- Every step that judges the previous one runs in a new session.
- `/approve` produces evidence and no verdict; a human sets
  `status: approved`.
- Stop condition at round three: split the phase rather than revise again.

### Task graph
- Machine-readable `tasks:` frontmatter carrying `deps`, `status`, and
  `files` per task, with the prose in the body and no duplication between
  them.
- `plan lint` catches cycles, unknown or forward dependencies, tasks done
  ahead of their dependencies, empty file lists, missing `Verify:` lines, and
  graph/body drift. `/review` and `/approve` both run it.
- `plan next --parallel` groups runnable tasks by file overlap.
- `plan done` refuses a task whose dependency is unfinished.

### Context
- `plan brief` computes a bounded read list: `AGENTS.md`, the phase file,
  direct dependencies' files, then the task's own. Build reads that and
  nothing else, in that order, so the cache prefix stays stable across the
  phase.
- An unlisted file stops the session instead of widening it.
- Search delegated to a subagent returning `file:line`.
- Handoffs appended to `docs/plans/NN-slug.log.md`, ten lines maximum.

### Build
- A task is done only when its `Verify` command has run and its output is
  shown.
- Explicit rule for when two tasks may share a session.
- Correction harvesting moved to `/close`, where a one-task-per-session
  workflow can actually count repeats.
