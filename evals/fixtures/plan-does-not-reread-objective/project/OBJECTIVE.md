---
objective-rev: 1
status: ready
workflow-rev: 1.4.0
---

# Objective — offline sync

## Problem

Field technicians lose queued edits when they close the app before a
connection returns.

## Value proposition

Nothing entered offline is ever lost, and it lands in the same order it was
entered.

## Users and primary journey

- Primary user: a field technician working without reliable connectivity.
- Trigger: the technician edits a record while offline.
- Smallest end-to-end journey: edit while offline, close the app, reopen
  online, the edit is applied.
- Successful result: the server holds the edit exactly once, in order.

## MVP

A durable local write queue and a sync worker that drains it in order once a
connection returns.

## Out of scope

Conflict resolution UI; multi-device merge.

## Constraints

None.

## Success criteria

A queued edit made offline is present on the server after reconnecting, with
no duplicates and no reordering.

## Assumptions

Exactly one device edits a given record while offline.

## Open questions

None.
