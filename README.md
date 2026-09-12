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
.coldsession/install.sh . --agent both --preview
.coldsession/install.sh . --apply <preview-id>
```

Windows PowerShell:

```powershell
git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
.\.coldsession\install.ps1 -Target . -Agent both -Preview
.\.coldsession\install.ps1 -Target . -Apply <preview-id>
```

Both installers use `bin/cs_install.py`. Their default action saves and prints
a preview; `--apply ID` / `-Apply ID` applies exactly that saved preview. Agent
selection (`claude`, `codex`, `both`) is captured by the preview. `--keep` /
`-Keep` remains accepted; the checkout is always retained for recovery.

The preview reports installation changes, customized files, conflicts,
versioned document migrations, readiness consequences, and reconciliation.
The installer refuses active stages, task claims, or assignment groups.
Settle workers first. Explicit `plan replan --recover-claims` recovers abandoned
workflow claims; elapsed time alone never establishes abandonment.

Apply rechecks the preview's inputs, stages replacements, backs up every
affected file with its checksum, and records an upgrade journal. It never
runs project verification commands or changes application implementation.
Unmodified managed files update automatically. Customized commands are preserved
and reported; runtime/template conflicts block application. Unrelated settings,
permissions, models, and hooks are preserved. Unknown legacy files are treated
as customized. `--baseline <known-release-checkout>` / `-Baseline <path>` enables
comparison against a known release when ownership records are absent.

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

Claude invokes `/cs-build T1`; Codex invokes `$cs-build T1`. Existing command
names are retained, including the deprecated explicit `cs-recheck` alias.
Commands provide instructions; they do not select the active model or guarantee
a new session. Use a fresh session for independent review and close.

`cs-define` records the product objective. `cs-plan` creates one bounded phase.
Carry durable product constraints into PLAN.md and each phase's Constraints
section so later phases retain requirements without rereading the objective.
Before implementing, understand affected behavior and existing capabilities.
Prefer reuse, configuration, standard-library/native solutions, and an extension
of existing code. Add an abstraction only for demonstrated needs.

Preserve correctness, security, data integrity, and accessibility, including
necessary error handling. Necessary work beyond the approved specification or
writable scope requires revision. Do not silently expand the contract.

Reviewers receive neutral requirements and artifacts, record independent
findings before author discussion, and may produce a clean review. Each finding
must identify a concrete defect or unnecessary complexity and its consequence.
Linter warnings are advisory; they do not automatically become blocking findings.

`cs-approve` records readiness, never human approval. After a clean check, the
human edits the phase to `status: approved`. Teammate plan approval does not
replace this step. Hooks reject supported agent edits introducing approval;
native sandbox, permissions, and hook trust remain authoritative.

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
Perform manual/visual checks yourself, then supply `--attest "observed result"`.
The attestation describes all declared manual/visual checks and is stored as
operator evidence, separate from automated exit status.

Verification records commands, results, exit status, truncation/timeout flags,
specification fingerprint, and content fingerprints for writable/supporting
files and dependency outputs. Output is bounded and likely credentials are
filtered before persistence. Commands must express their own expected-result
assertions and exit zero on success. Checks that change relevant inputs require
a rerun. `plan done` requires current successful evidence. Close rechecks all
evidence, including historical completed tasks.

The specification fingerprint includes task definitions, dependencies, scope,
acceptance/verification instructions, and constraint prose. Operational task
status, owner, stage markers, findings, and changelog do not change it. Edits to
the contract invalidate review/readiness even without a revision bump.

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
plan verify T1 [--attest "observed result"] [--timeout SECONDS]
plan done T1 / block T1 "reason"
plan findings [--open] / resolve F1 resolved|accepted|open "note"
plan bump / reviewed / metrics
plan replan [--recover-claims]
plan doctor [--json]
plan recover
plan guard read|write|lint|stage
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

Both adapters normalize supported file, patch, and shell payloads into shared
checks. Read access does not grant write access. Sensitive-file restrictions and
resolved path scope checks apply to supported file tools. During active builds,
shell payloads that cannot be proven within scope are refused; use scoped file
tools, filename discovery, or recorded verification. Unrelated projects stay quiet.
Explicit mutations fail with actionable errors when workflow state is invalid.

Arbitrary programs, network access, MCP tools, unregistered tools, direct human
edits, and harnesses without trusted hooks remain enforcement gaps. Verification
commands execute under native permissions and must be reviewed. This workflow
is not an operating-system security boundary.

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
