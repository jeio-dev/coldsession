---
phase: 02-<slug>
rev: 1
status: draft
workflow-rev: 1.0.1
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

<!-- F1 | Critical | Task ordering | T3 | description | recommended fix -->

## Changelog

<!-- rev 2: F1 -> resolved, T3 now depends on T2 -->
