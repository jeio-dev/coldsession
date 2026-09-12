---
description: Implement one approved task, verify it, commit, stop
argument-hint: [task-id] [--resume]
---

Parse `$ARGUMENTS` as one task ID plus optional `--resume`. If the ID is blank,
run `.claude/bin/plan recommend` and stop.

If invoked with a supervised assignment receipt, use its neutral brief and
implement only assigned source files. Return task/spec/assignment IDs and the
result to the coordinator. Skip all workflow mutations, verification execution,
handoff persistence, and commits below; the coordinator owns them.

Run `.claude/bin/plan start <task-id> [--resume]` first and inspect only its
output. If it refuses, print that output and stop before reading files. A task
already `in_progress` continues only with explicit `--resume`; done, blocked,
unapproved, and dependency-blocked tasks cannot start.

Then run `.claude/bin/plan brief <task-id>`.

## Reading

The brief's `read` block gives the file order, starting with AGENTS.md. Use
inlined context and follow the phase/handoff annotations. Use bounded read-only discovery to locate affected behavior and existing capabilities.
`files` authorizes writes; `reads` supplies supporting context. Correct an insufficient
brief before implementation. Keep search results concise.
Read relevant sections of large files and inherited dependency files as needed;
the read list is not a requirement to load every file in full. Keep generated
outputs such as lockfiles in writable scope and use their normal generator.
W07 is advisory; never drop required files or real dependencies just to lower it.

## Doing

Restate the acceptance criteria and Verify line, then implement only this task.
Do not change architecture, the plan, or another task.

Understand the affected behavior and preserve its existing contract. Before writing, take the
lowest rung that satisfies it: an existing capability, a configuration change,
an extension of existing code, a new file, a new abstraction, in that order.
Prefer a native or already-present primitive over a new component. Prefer the standard library and existing native capabilities. Preserve correctness,
security, data integrity, and accessibility, including necessary error handling.
If necessary work exceeds approved writable scope or requirements, stop and
request revision through the existing findings/replan loop. Add an abstraction
only for demonstrated needs.

If the task was specified a rung higher than it needs, implement the lower rung
that meets the criteria and record the mismatch in the phase log. That is not a
blocker.

Run `.claude/bin/plan verify <task-id>` to execute every declared automated check.
For `Verify: manual: ...` or `Verify: visual: ...`, perform the exact action and
run verification with `--attest "observed result"`. Attestations remain distinct
from automated evidence. Rerun verification after relevant files change.

On success:

1. Record a bounded handoff through `.claude/bin/plan handoff <task-id> <literal-JSON-object>`:
   decisions, evidence, limitations, affects (task IDs), provenance, and supersedes
   (prior handoff IDs). Use empty lists or "none" where appropriate; no diff summary.
   Keep the JSON at most 4096 characters. Quote it as a literal shell argument;
   the runtime writes the handoff, so no scratch source file is required.
2. `.claude/bin/plan done <task-id>` — it accepts only `in_progress` tasks.
3. Commit task changes, phase state, and log together with the task ID in the
   message.
4. Print `.claude/bin/plan recommend` and stop.

For a supervised worker assignment, implement only the assigned source files and
return the assignment result. The coordinator runs verification, writes handoffs,
completes tasks, and commits. Workers never run workflow mutations or nested fanout.

On a blocker, run `.claude/bin/plan block <task-id> "reason"`, add the next
open High Risk finding with its concrete unblock action, print
`.claude/bin/plan recommend`, and stop.
