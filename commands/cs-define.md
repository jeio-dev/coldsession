---
description: Turn a rough idea into a scoped objective brief
argument-hint: [rough app idea]
---

Help me turn this idea into a well-defined objective I can hand off for
detailed planning:

$ARGUMENTS

If the line above is blank, ask me for the idea and stop.

Produce an Objective Brief containing:
- Problem statement: what problem this solves, and for whom
- Core value proposition, in one or two sentences
- Primary users and their main use case
- MVP feature list: the smallest version that delivers the value proposition
- Explicitly out of scope for v1
- Constraints: platform, tech stack preferences, budget, timeline,
  integrations, hosting
- Success criteria: how we'll know the MVP works
- Open questions you need me to answer before planning can start

Ask me the open questions directly. Do not guess at answers.
Do not break this into tasks or phases. Do not write code.

## Next

Once I have answered the open questions, end with one line telling me what to
run next. Nothing is on disk yet, so decide it from the repo:

- An empty or near-empty repo, or no AGENTS.md: `/cs-groundwork` — the ground
  rules have to exist before there is anything to plan against.
- An existing codebase: `/cs-plan`, in this session, since it uses this brief.

From /cs-plan onward, `.claude/bin/plan recommend` computes the next step from
the phase file. Say so, so I stop needing to remember the order.
