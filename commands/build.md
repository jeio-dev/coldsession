---
description: Implement one approved task, verify it, commit, stop
argument-hint: [task-id]
---

Run `.claude/bin/plan brief $1`.

If $1 is blank, run `.claude/bin/plan next` and stop: tell me the runnable
task IDs and let me choose. If the brief prints BLOCKED, stop.

## Reading

Read exactly the files the brief lists, in the order it lists them, starting
with AGENTS.md. Nothing else. That order is fixed so the cached prefix is
reused across build sessions; do not read anything before it or reorder it.

If you need a file the brief does not list, stop and say which one and why.
That is a bug in the plan's `files` list, not something to work around.

If you need to locate something rather than read something, dispatch a search
subagent and take back the file:line answer only. Do not fill this session
with search output.

## Doing

Implement task $1 only. Do not change the architecture or the plan. Do not
start the next task. Restate the acceptance criteria and the Verify line
before you begin.

A task is done only when you have run its Verify command and shown me the
output. Not "the tests should pass" — the run, and what it printed. If there
is no runnable check, say so explicitly and tell me the single manual step I
have to take.

## Finishing

When the Verify output is clean:
1. `.claude/bin/plan done $1` — do not hand-edit the frontmatter.
2. Commit, with the task ID in the message.
3. Append to docs/plans/(NN)-(slug).log.md, ten lines maximum:
   `## $1` then only what the next session cannot work out from the repo —
   a decision you made that the plan did not specify, a gotcha you hit, a
   file whose actual contents differ from what the plan assumed. If there is
   nothing, write "nothing to carry". Never summarize the diff; git has it.
4. Run `.claude/bin/plan next` and print the result.
5. Stop. Exit the session rather than compacting.

If you hit a blocker:
- Stop. Do not work around it.
- `.claude/bin/plan block $1 "one line reason"`.
- Write it into the phase file as finding F(n) and tell me to re-enter at
  /review.
