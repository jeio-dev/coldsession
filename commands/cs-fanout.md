---
description: Dispatch one approved group through an explicitly selected team backend
argument-hint: [--backend orca|codex|claude] [--max N]
---

Run only on explicit user invocation. One agent is the default. Parse
`--backend orca|codex|claude` (default: the active harness, or Orca in an Orca
workspace) and `--max N` (default 2). Dispatch exactly one approved group.

You are the coordinator and sole writer of phase state, handoffs, and Git
commits. Phase Markdown is authoritative; harness task lists and messages
only arrange execution. A worker may never fan out or take over coordination.

Run `.claude/bin/plan doctor --json`, `.claude/bin/plan status`, and
`.claude/bin/plan next --parallel`. Check capability and `session_identity_detected` before claiming tasks.
If the coordinator has no stable harness identity, retain manual builds:

- Orca: resolve the CLI from the current workspace and run its status and
  orchestration capability checks. Use the installed Orca orchestration skill
  and its actual CLI schemas. Missing orchestration is unavailable, not a
  reason to install a plugin or change permissions.
- Codex: require native spawn, message, and wait tools in this session. Use
  those tools directly, with a fresh bounded assignment; do not launch nested
  Codex shells or assume CLI presence means subagent tools are available.
- Claude: require enabled agent-team creation, teammate messaging, and task
  tools. Agent teams can be disabled even when Claude is installed. Do not
  enable them or switch permissions implicitly.

If unavailable, report the exact missing capability, print the parallel group
readout, and retain manual `/cs-build <id>` execution. Do not claim tasks.

Run `.claude/bin/plan assign <backend> --max <N>`. Its atomic receipt includes
each task ID, specification fingerprint, unique assignment ID, writable files,
supporting reads, verification instructions, and expected result fields.
It accounts for running tasks and normalized paths. Do not dispatch a second
group in this invocation. Include `.claude/bin/plan brief <id>` output with
each assignment, including constraints and relevant dependency handoffs.

Create one worker per receipt using the selected backend. Instruct workers to
wait for your ready message before accessing files. Bind the stable worker
session/terminal ID from each dispatch receipt with
`.claude/bin/plan assign --bind <task-id> <worker-session-id>`, then send ready.
If the backend exposes no usable worker identity, report that enforcement gap
and keep workers stopped; settle claims explicitly before manual execution.
Tell every worker:

    Implement only the assigned source files. Understand affected behavior and
    reuse existing capabilities. Preserve correctness, security, data integrity,
    and accessibility. Use bounded read-only discovery; if the brief is
    insufficient, report a blocker before expanding implementation scope.
    Do not run plan start/done/verify, edit shared workflow files, commit,
    launch teammates, or perform operations on shared resources. Return task,
    spec, assignment, outcome (success or blocked), decisions, evidence,
    limitations, and changed file references. Carry all receipt IDs exactly.

Where the backend supports per-worker environment, set
`CS_WORKER_ASSIGNMENT=<assignment-id>`. Otherwise include it as an explicit
worker contract; doctor cannot attest enforcement of per-worker environment.

Wait for all workers. A quiet worker remains assigned. Never replace, restart,
or release one solely because of elapsed time. Answer only questions settled
by the approved phase. For a blocker that invalidates the phase, stop
integration, preserve worker changes, settle outstanding workers, and require
`.claude/bin/plan replan --recover-claims` followed by fresh review and human
approval. Teammate plan approval cannot replace human phase approval.

Validate returned task/spec/assignment against the receipt. Pass each result as a literal JSON argument to the runtime; no scratch file
outside task scope is required.
For each success, serialize `.claude/bin/plan verify <id>`, then
`.claude/bin/plan integrate <literal-result-JSON>`. Record a bounded handoff with
`.claude/bin/plan handoff <id> <literal-handoff-JSON>` and commit only after integration.
Reject superseded results. Serialize verification and all shared-resource work.

Report task outcomes, unresolved limitations, and
`.claude/bin/plan recommend`. Cold review remains a separate fresh-session
handoff containing neutral requirements and artifacts, without author advocacy.
