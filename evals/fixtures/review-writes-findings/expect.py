"""Grades /cs-review against an unreviewed phase with a real ordering gap.

T2's goal text says it builds "on top of the row shape T1 defines", but the
frontmatter gives T2 `deps: []` and a `files` list that omits
`src/db/schema.ts` -- exactly the template's own canonical F1 example
(README.md's Findings section, templates/phase.md). A competent first review
must catch it. If a reworded cs-review.md quietly stopped writing findings,
this is what would ship green without this fixture.
"""


def grade(ctx):
    failures = []

    status = ctx.plan("status")
    findings = ctx.plan("findings")
    lint = ctx.plan("lint")

    if "status draft" not in status.stdout:
        failures.append(
            "phase status is no longer draft; /cs-review must never change "
            f"phase status itself:\n{status.stdout}"
        )
    if "reviewed never" in status.stdout:
        failures.append(
            "`reviewed:` was never recorded; `plan finish review` did not run"
        )
    if "active none" not in status.stdout:
        failures.append("the active review marker was not cleared")
    if "no findings recorded" in findings.stdout:
        failures.append(
            "the review recorded no findings; the T1/T2 ordering gap in the "
            "fixture (T2 needs schema.ts from T1 but has no dep or files "
            "entry for it) should have been caught"
        )
    if "E12" in lint.stdout:
        failures.append("a finding line failed to parse (E12)")
    if "E13" in lint.stdout:
        failures.append("a finding id was reused (E13)")

    return failures
