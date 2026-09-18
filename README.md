# coldsession

A repository-owned planning workflow for Claude Code and Codex. Review runs
in a fresh session; humans approve the specification; completion requires
verification that matches the current requirements and relevant files.
The runtime and installers use Python's standard library (Python 3.9+).

## Install or upgrade

Existing project-local installations remain unchanged until explicitly applied.
These commands fetch the latest code from the default branch (`main`).
Keep the checkout until validation and recovery are complete:

```bash
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.coldsession/install.sh
# Review the short summary, then copy and run the command it prints.
```

Windows PowerShell:

```powershell
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.\.coldsession\install.ps1
# Review the short summary, then copy and run the command it prints.
```

The first command changes nothing. It prints a short preview and the exact
second command to copy and run. That second command applies only the saved
preview. Agent selection (`claude`, `codex`, `both`) is carried forward
automatically. The checkout is retained for recovery.

For automation or troubleshooting, add `--json` / `-Json` to receive the full
machine-readable preview. The explicit `--preview` / `-Preview`, `--apply ID` /
`-Apply ID`, `--baseline` / `-Baseline`, and `--keep` / `-Keep` options remain
available for advanced use.

The beginner preview reports how many managed files will change, whether local
customizations will be kept, and the next command. JSON mode includes file-level
changes, conflicts, versioned document migrations, readiness consequences, and
reconciliation.
The installer refuses active stages, task claims, or assignment groups.
Settle workers first. Explicit `plan replan --recover-claims` recovers abandoned
workflow claims; elapsed time alone never establishes abandonment.

Apply rechecks the preview's inputs, stages replacements, backs up every
affected file with its checksum, and records an upgrade journal. It never
runs project verification commands or changes application implementation.
Unmodified managed files update automatically. Windows line-ending conversion
is repaired automatically and is not treated as a customization. Customized
commands are preserved and reported; runtime/template conflicts block
application. Unrelated settings, permissions, models, and hooks are preserved.
Unknown legacy files are treated as customized; advanced JSON output explains
when a known-release baseline is needed.

On failure, the installer restores affected files. An incomplete journal blocks
workflow mutations. Run `install.sh <project> --recover` or
`install.ps1 -Target <project> -Recover` from the retained release checkout.
Recovery is idempotent and refuses to overwrite intervening changes. Backups
remain under `.coldsession-state/backups/<id>/`; preserve them until reviewed.
A repeated application of a completed preview reports completion without
reapplying it.

**Installation success and phase readiness are separate.** Start a fresh agent
session after upgrading, run `plan doctor`, resolve migration findings, obtain
fresh review and human approval where required, then rerun verification through
the normal workflow. Do not infer readiness from a successful install.

## Installed surfaces

| Path | Purpose |
|---|---|
| `.claude/commands/cs-*.md` | Claude slash commands |
| `.claude/bin/plan{,.cmd}` | Claude runtime |
| `.claude/hooks/cs-guard-*` | Claude hook adapters |
| `.claude/settings.json` | Merged hook registration |
| `.agents/skills/cs-*` | Codex skill adapters |
| `.agents/coldsession/commands/` | Canonical command copies for Codex |
| `.agents/coldsession/bin/plan{,.cmd}` | Codex runtime |
| `.codex/config.toml` | Delimited managed Codex hook registration |
| `templates/` | Objective, plan index, and phase templates |
| `.coldsession-state/` | Installation ownership, previews, journals, backups |

In examples below, `plan` means the installed runtime path. On PowerShell use
its adjacent `plan.cmd`. Launch the harness from the repository root.
Commit the selected adapters, templates, ownership record, and durable workflow
documents. Treat upgrade backups and diagnostic artifacts according to project
retention rules; they can contain copies of local configuration.

## Workflow

`cs-define -> cs-groundwork? -> cs-plan -> cs-review -> cs-revise? -> cs-approve -> cs-build -> cs-close`

`cs-issue <change request>` is an optional backlog command outside that phase
sequence. It creates one GitHub issue for a coherent change, or prints a draft
with `--draft`. Issues record the goal, observed state, expected behavior,
acceptance criteria, and references. They do not create phase tasks or grant
approval. Incorporate an issue through new phase planning or explicit replan
when ready.

`cs-plan --issue <number>` plans one open issue from the current GitHub
repository into exactly one normal phase. It first runs the read-only
`plan issue <number>`, which refuses before any workflow document changes when
the current phase is not closed, `active: plan` lacks `--resume`, `gh` is
missing or unauthenticated, retrieval fails, the issue is not open, or a phase
already records the issue. Plan treats
the issue body as proposed requirements: numbered steps are candidates, durable
constraints win, and conflicts become the normal planning questions. The phase
copies the agreed goal and acceptance criteria, defines its own scope,
dependencies, and verification, and records the issue URL, update time, and
body SHA-256 in `## Source`. That section is provenance inside the reviewed
specification, so the phase stands alone without GitHub and later issue edits
change nothing until an explicit replan, review, and human approval. It ends at
the normal `cs-review` handoff; it never approves, builds, closes the phase, or
closes the issue. `cs-build` still takes only task IDs and refuses an issue
number.

Claude invokes `/cs-build T1`; Codex invokes `$cs-build T1`. Existing command
names are retained, including the deprecated explicit `cs-recheck` alias.
Commands provide instructions; they do not select the active model or guarantee
a new session. Use a fresh session for independent review and close.

`cs-review` is the single entry point for a review round. It records the
independent review and, when `plan recommend` returns `cs-revise`, immediately
runs one Revise pass in the same session. A clean review stops at Approve; a
substantive revision stops at Review, which must run in a new session. The
standalone `cs-revise` command remains available for explicit recovery and
resume.

`cs-define` records the product objective. `cs-plan` creates one bounded phase.
Carry durable product constraints into PLAN.md and each phase's Constraints
section so later phases retain requirements without rereading the objective.

Commands that need decisions from you ask in numbered rounds. A round is every
question whose prerequisites are already settled, asked together, each with a
recommended answer so the round can be accepted whole. Facts the repository can
answer are searched, not asked. `cs-define` asks until nothing is left open;
`cs-plan` asks one round, at most two, and a third means the phase should be
split; `cs-issue` asks one round only when a question blocks publishing.

Work is sized at the lowest rung that holds: no task because an existing
capability covers it, a configuration change, an extension of existing code, a
new file, then a new abstraction. `cs-plan` sizes tasks this way because a task
a rung too high widens `files`, the scope a Build session is bounded to.
`cs-build` implements the lower rung when the plan overshot and notes it in the
phase log. `cs-review` names the rung an over-built task should have stopped at.
Before implementing, understand affected behavior and existing capabilities,
and prefer standard-library and native solutions.

Preserve correctness, security, data integrity, and accessibility, including
necessary error handling. Necessary work beyond the approved specification or
writable scope requires revision. Do not silently expand the contract.

Reviewers receive neutral requirements and artifacts, record independent
findings before author discussion, and may produce a clean review. Each finding
must identify a concrete defect or unnecessary complexity and its consequence.
Linter warnings are advisory; they do not automatically become blocking findings.

When only cosmetic Low findings remain, `cs-revise` can record reasoned
acceptances without changing the specification. In format 2, it does not bump
the revision and ends with `plan finish revise --accept-only`; the runtime
requires the existing review fingerprint to match, logged Low acceptances,
and no open findings. The next step is the independent approval checklist,
then human approval. Substantive edits, Medium settlements, bumped revisions,
and legacy phases still require a revision review. A document-only change can
alter the contract, so the number of document-only commits never waives review.
Revise keeps a temporary hashed snapshot in `.coldsession-state/` to distinguish
this pass's settlements from earlier fixes, verify scoped implementation files
did not change, and support resume; successful finish removes it. Missing or
stale snapshot evidence requires the normal bump/review path.

`plan findings --open` surfaces repeated reopens and recent settlement notes.
After two reopens, resolve the exact stated ask and cite the changed target;
repeating verification is insufficient for a requested text edit. Reasoned
acceptances stand unless contradicted by evidence or an unaddressed material
consequence. Settlement notes reject multiline/pipe-delimited content and
redact likely credentials. There is no target acceptance rate.

Revise and Close commit their authorized changes after stage finish writes the
workflow documents, preserving unrelated work. Explicit project/user commit
restrictions take precedence. Required CI evidence identifies a run, tested
commit, and job conclusions; a local result or branch push alone is insufficient.

`cs-approve` records readiness, never human approval. After a clean check, the
human edits the phase to `status: approved`. Teammate plan approval does not
replace this step. Hooks reject supported agent edits introducing approval;
native sandbox, permissions, and hook trust remain authoritative.

When you cannot edit the file yourself, for example from a phone or a remote
session, type `/cs-grant` (Codex: `$cs-grant`) as a prompt instead. The
UserPromptSubmit hook, not the agent, sets `status: approved`, and only when
the current revision carries the `/cs-approve` ready marker, its specification
is unchanged since, lint is clean, and no finding is open. Otherwise the hook
blocks the prompt with the reason (E34). A grant runs only from the hook's
prompt event, never from `plan guard` arguments. It trusts whoever can submit
a prompt to the session, so do not let an orchestrator relay `/cs-grant` to a
worker terminal. Without trusted hooks nothing is approved; edit the file.

## Format 2 contract

```yaml
---
phase: 01-example
rev: 1
status: draft
workflow-rev: 2.0.0
tasks:
  T1: {deps: [], status: pending, files: [src/store.py], reads: [docs/schema.md]}
---
```

Each task has a matching `## T1 - title` with Goal, Deliverables, Acceptance
Criteria, and verification. `files` names exact writable repository files;
optional `reads` names supporting context. Paths cannot be directories, globs,
traversals, absolute paths, or escapes through symlinks/Windows junctions.
Duplicate task IDs are rejected. Bounded read-only discovery is permitted;
correct an insufficient brief before implementing outside its contract.

Use one verification declaration per line:

```text
Verify: `python -m unittest discover -s tests` exits 0
Verify: manual: inspect the exported totals against the supplied example
Verify: visual: tab through the dialog; focus reaches Save and Cancel
```

`plan verify T1` executes the automated commands from the repository root with
a configurable timeout (`--timeout SECONDS`, default 300, maximum 3600).
Perform each manual/visual check yourself, then identify every observation with
its kind and one-based index, for example:

```text
plan verify T1 --attest manual:1="exported totals match" --attest visual:1="focus reached Save and Cancel"
```

A task with exactly one non-automated check also accepts the legacy unlabelled
form. Multiple checks always require separate labelled attestations. Each receipt
is bound to the declared check's hash and stored as operator evidence, separate
from automated exit status. Missing receipts are reported before commands run or
existing evidence changes.

Verification records commands, results, exit status, truncation/timeout flags,
task-scoped specification fingerprint, and content fingerprints for
writable/supporting files and dependency outputs. Attempts are append-only, and
the record points to the latest successful attempt without allowing a later
failure to count as success. Output is bounded and likely credentials are
filtered before persistence. Commands must express their own expected-result
assertions and exit zero on success. Checks that change relevant inputs require
a rerun. `plan done` requires current successful evidence. Close rechecks all
evidence, including historical completed tasks.

The phase-wide specification fingerprint includes every task definition,
dependency, scope, acceptance/verification instruction, and constraint. It gates
review/readiness. Evidence uses a separate task fingerprint containing shared
constraints plus that task and its transitive dependency contracts, so unrelated
later-task edits do not invalidate it. Working-file fingerprints remain a
separate check. Operational task status, owner, stage markers, findings, and
changelog do not change either specification fingerprint.

`plan replan` preserves completed work and findings, resets unfinished work to
draft, increments the revision, and clears readiness. Closed historical phases
remain read-only. Settle workers before explicitly recovering active claims.
A blocker stops integration; preserve changes and renew review before proceeding.

## Context and handoffs

`plan brief T1` includes the task, applicable constraints, direct file references,
and relevant dependency handoffs. Format 2 does not automatically include every
transitive dependency source file. Estimates are labeled as bytes/4 estimates;
they are not measured model tokens. Stable ordering may help cache reuse, but
coldsession makes no prompt-cache guarantee.

`W07` is an advisory file-context estimate above 12,000 tokens, not an
installation failure or an approval blocker. It counts whole task files and
explicit supporting reads, once per resolved path. Shared AGENTS.md, the phase
file, and inherited legacy dependency files are reported separately. Recognized
package-manager lockfiles (including package-lock.json) are also reported
separately unless explicitly listed in `reads`. They stay in writable scope
and verification fingerprints; do not remove required outputs to silence W07.
Completed tasks and closed phases do not emit W07. A small edit
to a large existing file can still trigger it: inspect `plan brief T1`, use
targeted reads, and keep required files in scope. Other source files, generated
types, and documentation still count at full size; this is a file inventory,
not measured prompt usage. Split a task only when its work is actually too broad;
keep real dependency edges. Existing installations need an explicit upgrade
to receive runtime fixes; changing this checkout alone does not update them.
Older review commands may promote every warning to a Medium finding; update
those adapters too. Warnings alone do not establish a review finding.

Record bounded structured handoffs with `plan handoff T1 handoff.json` or
`plan handoff T1 --stdin`. A literal JSON object argument also works, without
creating a scratch file. `plan integrate` accepts the same input forms. Required fields are `decisions`, `evidence`,
`limitations`, `affects` (task IDs), `provenance`, and `supersedes` (handoff IDs).
Use arrays, including empty arrays, for `affects` and `supersedes`; use `"none"`
only for an empty string field.
Each entry is limited to 4096 characters. The runtime stamps identity, task,
specification, and time. Briefs retrieve at most eight relevant non-superseded
entries, rather than the latest global entry. Historical Markdown logs remain
readable.

## Commands and persistence

```text
plan status / recommend / lint / next [--parallel]
plan brief T1
plan begin review|revise|approve|close [--resume]
plan finish review|revise|approve|close [--pass|--fail]
plan start T1 [--resume]
plan verify T1 [--attest kind:N="observed result"]... [--timeout SECONDS]
plan done T1 / block T1 "reason"
plan findings [--open] / resolve F1 resolved|accepted|open "note"
plan bump / reviewed / metrics
plan replan [--recover-claims]
plan doctor [--json]
plan recover
plan guard read|write|lint|stage
plan issue NUMBER [--resume]
```

Mutations hold one repository lock, including verification and shared-resource
operations. Unavailable locks refuse mutation. A long-running command never
loses its lock because of age. If a process dies, confirm it is stopped and
remove only the exact lock path reported by the refusal; then rerun. Workflow
claims are recovered separately through replan.

File replacements are atomic. Multi-file close, assignment, and recovery
operations use a journal with before/after contents. `plan recover` replays an
interrupted transaction idempotently and refuses conflicting intervening edits.
The phase index remains on the closed phase until planning creates the next one.

## Hooks and doctor

`plan doctor --json` reports Python/runtime versions, adapter installation,
detected CLIs, hook configuration, unknown trust, pending journals, and enforcement
gaps. Configuration on disk does not prove that a running harness trusts or loads
it. Start a fresh session and confirm native hook trust after installation.

Both adapters normalize supported file and patch payloads into shared checks.
Read access does not grant write access. `Read` and content-returning `Grep`
must name a file in the active brief; filename-only discovery remains available.
Sensitive-file restrictions and resolved path scope checks apply to supported
file tools. Writes to Claude's resolved temporary `claude/.../scratchpad`
subtree are also allowed. Unrelated projects stay quiet.
Explicit mutations fail with actionable errors when workflow state is invalid.

Shell commands, arbitrary programs, network access, MCP tools, unregistered
tools, direct human edits, and harnesses without trusted hooks remain enforcement
gaps. Shell and verification commands execute under native permissions and must
be reviewed. This workflow is not an operating-system security boundary.

Current interface references: [Codex hook configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude hooks](https://code.claude.com/docs/en/hooks), and
[Claude agent teams](https://code.claude.com/docs/en/agent-teams).

## Optional teams

`cs-fanout --backend orca|codex|claude --max N` dispatches one approved group;
default width is two. Capability checks happen before task claims. Unavailable
backends report their missing capability and retain manual execution. There is
no automatic plugin installation or nested fanout.

`plan assign <backend> --max N` atomically claims a nonconflicting group and
returns task IDs, spec fingerprints, unique assignment IDs, writable files,
reads, verification, and result expectations. After dispatch, bind each worker session with `plan assign --bind T1 <worker-id>`
before signaling it to start. A bound worker cannot be replaced without explicit
claim recovery. Stable harness identity is required for team execution.
Workers edit only assigned source files and return results. The coordinator alone verifies, writes handoffs and
workflow state, integrates matching results with `plan integrate result.json`,
and commits. Quiet workers remain assigned; elapsed time does not trigger
replacement. Set `CS_WORKER_ASSIGNMENT` where a backend supports per-worker
configuration; otherwise that boundary is a prompt contract, reported as a gap.

## Migration and release gates

Release 3.0 introduces phase format 2.0. Existing 1.x documents remain readable.
Explicit migrations are registered for 1.3, 1.4, and 1.5; unknown formats block
application. Legacy readable scope moves to `reads`, while ambiguous writable
scope remains empty with migration findings. Approval is renewed when contracts
change; semantically unchanged format-2 updates retain approval. Closed phases
are not rewritten. Migration preserves IDs, dependencies, findings, and completed
history, and never fabricates verification evidence. Implementation gaps become
reviewed corrective tasks; installers never repair application code themselves.

Run `python -m unittest discover -s tests -q` on Windows and Linux before release.
See [evals/README.md](evals/README.md) for opt-in, budgeted comparisons of direct
harness use, the baseline release, and this workflow. Include failed runs and
measure correctness, regressions, unnecessary changes, actual tokens when
available, elapsed time, and interventions. False findings require independent
adjudication. No live evaluation evidence means no quality/token improvement claim.

No database, vector store, daemon, model router, or automatic plugin installation
is required. MIT licensed.
