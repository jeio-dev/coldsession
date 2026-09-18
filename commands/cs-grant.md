---
description: Human approval from chat when you cannot edit the phase file
---

You did not approve anything. The human typed this command, and the prompt
hook has already done one of two things before this turn began: it set
`status: approved` on the current phase, or it refused and blocked the prompt.
Never write `status: approved` yourself, and do not edit the phase file.

Run `.claude/bin/plan status` and inspect only its output.

- If the phase is approved, say so in one line and end with the `next` line
  from the tool, verbatim. Build begins in a new session.
- If it is still a draft, the hook did not run: hooks are not installed,
  not trusted, or disabled on this surface. Say that approval did not happen,
  run `.claude/bin/plan doctor`, and tell the human to either fix the hooks or
  set `status: approved` in the phase file themselves. Do not offer to make
  the edit.
