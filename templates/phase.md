---
phase: 02-<slug>
rev: 1
status: draft
workflow-rev: 1.3.0
tasks:
  T1: {deps: [], status: pending, files: [src/db/schema.ts]}
  T2: {deps: [T1], status: pending, files: [src/sync/queue.ts, src/sync/types.ts]}
  T3: {deps: [T1], status: pending, files: [src/sync/worker.ts]}
  T4: {deps: [T2, T3], status: pending, files: [src/sync/index.ts]}
---

# Phase 02 — <name>

<One sentence: what runs at the end of this phase that does not run now.>

## T1 — <name>

Goal:
Deliverables:
Acceptance Criteria:
Verify: `<exact command>` prints/exits `<exact expected result>`

## T2 — <name>

Goal:
Deliverables:
Acceptance Criteria:
Verify: `<exact command>` prints/exits `<exact expected result>`

## T3 — <name>

Goal:
Deliverables:
Acceptance Criteria:
Verify: `<exact command>` prints/exits `<exact expected result>`

## T4 — <name>

Goal:
Deliverables:
Acceptance Criteria:
Verify: `<exact command>` prints/exits `<exact expected result>`

## Assumptions

## Open questions

## Out of scope

## Findings

<!-- /cs-review and /cs-recheck write here. One finding per line, seven fields:
     id | severity | category | tasks | status | description | recommended fix
     severity: Critical | High | Medium | Low
     status:   open | resolved | accepted   (set it with `plan resolve`)
     tasks:    comma-separated task ids, or - for a plan-level finding
     No pipes inside a description or fix; the parser splits on them.

F1 | Critical | Task ordering | T3 | open | T3 reads the queue but does not depend on T2 | add T2 to T3 deps
-->

## Changelog

<!-- `plan resolve` writes here. One line per resolution:
     rev N | F1 | resolved | the task id or plan line that now carries the fix
-->
