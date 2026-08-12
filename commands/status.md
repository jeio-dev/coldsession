---
description: Where the current phase stands
---

Run `.claude/bin/plan status` and `.claude/bin/plan next --parallel`.

Report in five lines or fewer: the phase and its status, what is done out of
how many, open findings if there are any, what is runnable now, and what is
blocked and why. If nothing is runnable, name the dependency holding it up.
End with the `next` line from the tool, verbatim. Read no files beyond what
the tool prints.
