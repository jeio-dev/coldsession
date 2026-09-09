---
phase: 01-sync
rev: 1
status: draft
workflow-rev: 1.4.0
tasks:
  T1: {deps: [], status: pending, files: [src/db/schema.ts]}
  T2: {deps: [], status: pending, files: [src/sync/queue.ts]}
---

# Phase 01 — sync

Ship an offline write queue backed by a new schema.

## T1 — schema

Goal: Define the sync queue's persisted row shape.
Deliverables: `src/db/schema.ts` exporting the `QueueRow` type and a `queueTable` definition.
Acceptance Criteria: `QueueRow` is exported and matches the queue's on-disk columns.
Verify: `npm test -- schema` exits 0

## T2 — queue

Goal: Implement enqueue/dequeue on top of the row shape T1 defines.
Deliverables: `src/sync/queue.ts` importing `QueueRow` from `src/db/schema.ts` and implementing `enqueue`/`dequeue`.
Acceptance Criteria: a round-tripped item keeps its `QueueRow` shape.
Verify: `npm test -- queue` exits 0

## Assumptions

None.

## Open questions

None.

## Out of scope

None.

## Findings

<!-- /cs-review writes here on every review round. One finding per line, seven fields:
     id | severity | category | tasks | status | description | recommended fix
     severity: Critical | High | Medium | Low
     status:   open | resolved | accepted   (set it with `plan resolve`)
     tasks:    comma-separated task ids, or - for a plan-level finding
     No pipes inside a description or fix; the parser splits on them. -->

## Changelog

<!-- `plan resolve` writes here. One line per resolution:
     rev N | F1 | resolved | the task id or plan line that now carries the fix -->
