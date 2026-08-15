# Changelog

The tool release and phase-file format are versioned separately. A phase file
records the format it was planned under as `workflow-rev`; `plan lint` checks
that against the supported format rather than the product release.

## [v2.0.0]

### One installer for install, update, and agent selection

- `install.sh` and `install.ps1` now handle fresh installs, idempotent updates,
  v1 migrations, and switching between Claude Code, Codex, or both.
- Interactive runs prompt for an agent selection; automation uses
  `--agent claude|codex|both` or `-Agent claude|codex|both`.
- The selected set is authoritative. Only recognized coldsession-managed
  artifacts are removed, while templates, phase files, unrelated commands and
  skills, and modified Claude settings are preserved.
- Removed `update.sh` and `update.ps1`; re-running the installer is the update
  path.

### Consistent `cs-*` entry points

- Renamed Claude commands to `/cs-define`, `/cs-build T2`, and the other
  `cs-*` names. The old unprefixed names are removed during migration.
- Renamed Codex skills to `$cs-define`, `$cs-build T2`, and matching `cs-*`
  names. Codex uses its native skill syntax, so only the sigil differs.
- Kept `commands/cs-*.md` canonical. Claude receives direct copies; Codex
  receives runtime-patched copies under `.agents/coldsession/commands/` and
  thin adapters under `.agents/skills/cs-*`.

### Codex support

- Added ten repository-scoped Codex skills under `.agents/skills/`, matching
  the existing Claude Code commands one-for-one.
- Each agent surface has its own runtime, so a Codex-only install has no
  dependency on `.claude/` and a Claude-only install has no Codex artifacts.
- Fixed Windows runtime detection so a non-functional Microsoft Store
  `python3.exe` shim no longer masks a working `python` command.

### Release and format compatibility

- `TOOL_VERSION` is now `2.0.0`; the unchanged phase format remains `1.3.0`.
- `plan version` reports the release version, while `plan lint` compares
  `workflow-rev` with the separate supported format version. Existing 1.x
  phase files therefore continue to lint after updating to v2.

## [v1.2.0]

### The loop closes at /plan, not /define

Finishing a phase sent you back to `/define`. `/close` said to run `/plan`,
"and `/define` first if its objective is more than one line in PLAN.md" — but
PLAN.md is defined as one line per phase and nothing else, so the condition
could never be read literally, and a session read it as intent instead: is
this more than one line's *worth* of design? For any phase worth having, yes.
`/plan` then bounced to `/define` on its own, because `/close` sends you to a
new session and `/plan` required an objective brief held in the session's own
memory. Both paths landed on a command that produces a whole-product MVP
brief — primary users, out of scope for v1, hosting — and writes none of it to
disk, at a point where the product scope was settled several phases ago.

`/close` now hands off to `/plan` and names the phase. `/plan` opened cold
falls back to what is on disk: the phase's line in PLAN.md, the closed phase
file and its log, AGENTS.md, and architecture notes. A one-line phase name is
an intention rather than a specification, so it asks its open questions before
writing, which it was already meant to do. `/define` goes back to being what
it is — the one-time front door.

### /close no longer points `current:` at a file that does not exist

`/close` advanced `current:` to the next phase file, which `/plan` had not
written yet. `read_index` refuses a pointer it cannot resolve and every
subcommand goes through it, so `plan status`, `plan recommend`, and `plan
brief` all failed between the two commands — the one moment the workflow's
"just run `plan recommend`" answer was unavailable. `/close` now leaves the
pointer alone and `/plan` moves it in the same edit that writes the file it
points at. When a pointer does dangle, the error says a phase was probably
closed without the next being planned, and names both ways out.

### A closed phase says what to do next

`/close` sets `status: closed` in the phase file. `recommend` returns `/plan`
for it instead of recommending the `/close` you just ran, `plan next` says the
same, and `lint` accepts the status. `E15` — approved with an open Critical or
High — now covers closed phases too, so moving a phase off `approved` does not
quietly retire the check.

## [v1.1.2]

### `plan brief` reads the full dependency chain

`plan brief` only pulled `files` from a task's *direct* deps. A phase shaped
like `T1 → (T2, T3) → T4` never surfaced T1's files in T4's brief, because T1
is not in T4's `deps` list — only in T2's and T3's. The build session then
either stalled on a missing file or went reading for it outside the bounded
list, defeating the point of a computed read list. `plan brief` now walks the
transitive closure of `deps` and pulls `files` from every ancestor task, not
just the immediate ones.

### An update script for existing installs

Install pins the tool's version into the project on purpose, but that meant
picking up a fix required redoing the whole install by hand. `update.sh`
(`update.ps1` on Windows) re-copies `.claude/commands/`, `.claude/bin/plan`,
and `.claude/bin/plan.cmd` from a fresh clone, refuses to run against a
project with nothing installed yet, and leaves `templates/` and
`.claude/settings.json` alone. Same clone-and-self-delete shape as install.

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
