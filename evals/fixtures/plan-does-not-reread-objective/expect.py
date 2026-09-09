"""Grades /cs-plan against a repo where PLAN.md already exists.

cs-plan.md is explicit: "Do not open, search, quote, or otherwise read
`OBJECTIVE.md`, even on `--resume`" once PLAN.md exists -- product scope has
already been reduced to the phase index. Machine state alone can't prove a
negative like "did not read this file", so this fixture grades the tool-call
trace instead of (in addition to) the resulting phase file.
"""


def grade(ctx):
    failures = []

    hits = ctx.tool_inputs_mentioning("OBJECTIVE.md")
    if hits:
        failures.append(
            f"{len(hits)} tool call(s) referenced OBJECTIVE.md after PLAN.md "
            "already existed, which the contract forbids"
        )

    plans_dir = ctx.tmp / "docs" / "plans"
    new_files = sorted(
        p for p in plans_dir.glob("02-*.md") if not p.name.endswith(".log.md")
    ) if plans_dir.exists() else []
    if not new_files:
        failures.append("no docs/plans/02-*.md phase file was written")
        return failures
    if len(new_files) > 1:
        failures.append(f"more than one 02-*.md phase file was written: {new_files}")

    lint = ctx.plan("lint")
    if lint.returncode != 0:
        failures.append(f"plan lint failed on the new phase:\n{lint.stdout}")

    plan_md = ctx.text("PLAN.md")
    if "current: docs/plans/02-" not in plan_md:
        failures.append(
            "PLAN.md's `current:` pointer was not moved onto the new phase"
        )
    if "[x] Phase 01" not in plan_md and "[x] phase 01" not in plan_md.lower():
        failures.append("Phase 01's checklist line was disturbed")

    return failures
