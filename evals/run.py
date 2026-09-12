#!/usr/bin/env python3
"""Run coldsession prompt evals: real cs-* commands against fixture repos.

Not wired into CI. Each run shells out to the real `claude` CLI against a
fixture project, which needs live credentials and spends real tokens -- a
deliberate deferral (see evals/README.md), not an oversight. Run this by
hand after reworking a commands/*.md file's prose, before opening a PR:

    python evals/run.py --live                   # every fixture
    python evals/run.py --live review-writes-findings # one fixture
    python evals/run.py --live --keep some-fixture       # keep the temp project dir

tests/test_evals.py exercises the grading logic in every fixture's expect.py
without spending tokens, by feeding it hand-built pre/post-run states; run
that as part of the normal test suite. This script is for actually driving
the model.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402


def run_one(name, keep=False, max_budget_usd=lib.DEFAULT_MAX_BUDGET_USD):
    prompt_path = lib.FIXTURES / name / "prompt.txt"
    if not prompt_path.exists():
        raise lib.FixtureError(f"{name}: no prompt.txt")
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    grade = lib.load_expect(name)

    tmp = Path(tempfile.mkdtemp(prefix=f"coldsession-eval-{name}-"))
    try:
        lib.setup_project(name, tmp)
        events, result = lib.run_claude(tmp, prompt, max_budget_usd=max_budget_usd)
        if result.truncated:
            return False, ['tool trace truncated; absence-based assertions cannot be trusted']
        if result.returncode != 0:
            return False, [
                f"claude -p exited {result.returncode}:\n{result.stdout}\n{result.stderr}"
            ]
        ctx = lib.EvalContext(tmp=tmp, events=events)
        failures = grade(ctx)
        return not failures, failures
    finally:
        if keep:
            print(f"  kept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("fixtures", nargs="*",
                         help="fixture names to run (default: all)")
    parser.add_argument("--keep", action="store_true",
                         help="keep every temp project dir instead of deleting it")
    parser.add_argument('--live', action='store_true', help='explicitly opt into paid model calls')
    parser.add_argument("--max-budget-usd", default=lib.DEFAULT_MAX_BUDGET_USD,
                         help="cap on API spend per fixture (default: %(default)s)")
    args = parser.parse_args()
    if not args.live:
        parser.error('live evaluation requires explicit --live; deterministic tests do not spend tokens')

    names = args.fixtures or lib.list_fixtures()
    if not names:
        print("no fixtures found under evals/fixtures/")
        return 1

    failed = 0
    for name in names:
        print(f"== {name} ==")
        try:
            ok, failures = run_one(name, keep=args.keep,
                                    max_budget_usd=args.max_budget_usd)
        except lib.FixtureError as exc:
            ok, failures = False, [str(exc)]
        if ok:
            print("  PASS")
        else:
            failed += 1
            print("  FAIL")
            for f in failures:
                print(f"    - {f}")

    print(f"\n{len(names) - failed}/{len(names)} fixtures passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
