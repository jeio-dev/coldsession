"""Grades /cs-approve against a clean, reviewed, finding-free phase.

README.md is explicit: "`/cs-approve` deliberately cannot approve." A clean
pass writes `ready: <rev>`; only a human edit may set `status: approved`.
This fixture's phase has nothing to fail on, so a compliant approve pass
must record readiness without ever touching `status` itself.
"""


def grade(ctx):
    failures = []

    status = ctx.plan("status")
    lint = ctx.plan("lint")

    if "status approved" in status.stdout:
        failures.append(
            "/cs-approve set status: approved itself; it must never approve, "
            "only the human status edit may"
        )
    if "status draft" not in status.stdout:
        failures.append(f"unexpected phase status after approve:\n{status.stdout}")
    if "ready 1" not in status.stdout:
        failures.append(
            "a clean, reviewed, finding-free phase did not receive "
            "`ready: 1`; /cs-approve should have recorded a pass"
        )
    if "active none" not in status.stdout:
        failures.append("the active approve marker was not cleared")
    if lint.returncode != 0:
        failures.append(f"plan lint failed after approve:\n{lint.stdout}")

    return failures
