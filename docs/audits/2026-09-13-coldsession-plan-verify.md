# Audit: coldsession `plan verify` invalidation and attestation behavior

Date: 2026-09-13
Repository state: Phase 03, revision 9
Tool: coldsession 3.2.0 (`.claude/bin/plan:50`; `.coldsession-state/installed.json:2`)

## Executive finding

Yes, the earlier verification sequence was produced by coldsession behavior, but it contains three different cases:

1. The T5 -> T4 -> T1/T3 dependency-error cascade is caused by coldsession's global phase-specification hash. Revision 9 changed T6's read list and verification prose, but that changed the specification hash stored for every task, invalidating otherwise unchanged T1-T5 evidence. This is conservative over-invalidation, not an application failure.
2. The final T5 "lacked an attestation" result is expected for the command that was run. `plan verify T5` was invoked without `--attest`, while T5 declares one visual and one manual check. The automated test passed 21/21; coldsession intentionally assigned `exit: null` to both non-automated checks.
3. The verifier has a separate evidence-integrity defect: one unstructured `--attest` value is copied to every visual/manual check. The previously committed T5 evidence proves that an Admin-only observation was copied into the Viewer-denial result and still made the whole task successful.

The transient T3 `LegacyDbSetupError` came from `supabase db reset`, not from coldsession's dependency or attestation logic. Its immediate retry succeeded with 9/9 tests. Coldsession did, however, overwrite the failed attempt when the retry ran, which is part of the evidence-history problem described below.

## Evidence

### A. Global hashing caused the dependency cascade

Before revision 9, the committed T1-T5 evidence all stored this specification hash:

```text
951b370efb4de9cd5bd2ce3e0b3f9e0a9cd50d43f4e85850e4a1d3f3701d5a23
```

After revision 9, every reverified task stored:

```text
6b1d080ad10875f7e9427b2edf26b6f12deffe5c04ae6c895a61a3bbb576c7b7
```

The relevant revision changed T6's `reads` and T6 verification instructions (`docs/plans/03-queue-reference.md:16`, `:450-452`). T1-T5's own task declarations and Verify lines did not change. Nevertheless:

- `plan verify T5` first failed with `T5 dependency evidence is missing or stale; run plan verify T4`.
- `plan verify T4` then failed with `T4 dependency evidence is missing or stale; run plan verify T1` and, after T1, required T3.
- T1, T2, T3, and T4 all passed when rerun with their existing file fingerprints/check hashes.

This follows directly from the implementation:

- `specification()` hashes the prose and the complete task map for the phase, not a task-scoped contract (`.claude/bin/plan:2279-2302`).
- dependency validation requires each dependency's evidence to match that phase-wide specification (`.claude/bin/plan:2527-2529`).
- revision 9 explicitly records that T6's read/verification plan changed and that T5 must be re-attested because T6 changed `app/admin/queues/page.tsx` (`docs/plans/03-queue-reference.md:629`, `:649`).

Conclusion: refreshing T5 itself was justified because a T5-owned page changed, but forcing T1-T4 to rerun for a T6-only planning change was a coldsession over-invalidation side effect.

### B. Missing T5 attestations were expected for the literal command

T5 declares three checks (`docs/plans/03-queue-reference.md:404-406`):

1. automated action tests;
2. a visual Admin table check;
3. a manual Viewer-denial check.

The command run was:

```text
.claude/bin/plan.cmd verify T5
```

It did not include `--attest`. In `cmd_verify`:

- the sole attestation is parsed from optional `--attest` (`.claude/bin/plan:2551-2555`);
- every non-automated check receives `exit: 0` only when that string is nonblank; otherwise it receives `exit: null` (`.claude/bin/plan:2563-2569`);
- all results must have `exit == 0` for task success (`.claude/bin/plan:2573-2584`).

The resulting `docs/plans/03-queue-reference.evidence.json` record confirms:

- automated result: exit 0, 21/21 tests passed;
- visual result: empty `attestation`, `exit: null`;
- manual result: empty `attestation`, `exit: null`;
- overall `success: false`.

The coldsession Build instructions do tell the operator to perform manual/visual actions and rerun with `--attest "observed result"` (`.claude/commands/cs-build.md`, "Run ... verify" paragraph). Therefore the missing-attestation failure is correct for a bare direct invocation; the verifier must not invent human observations.

### C. One attestation can falsely satisfy unrelated checks

The more serious issue is that the CLI accepts only one `--attest` string and writes it into every non-automated result without associating it with a check index or check text.

The committed pre-revision-9 T5 record is concrete evidence:

- T5 had the same visual Admin check and manual Viewer-denial check.
- Both result objects contain the identical Admin-only attestation beginning `Signed in as local active Admin...`.
- That text describes headings, rows, select options, and an Admin refile/revert. It does not attest that a Viewer received a 404 or that no queue data rendered.
- Both results nevertheless have `exit: 0`, and T5 has `success: true`.

The T5 handoff separately says a Viewer fetch returned 404, so the action may genuinely have been performed. The defect is that the authoritative verification record neither captures nor binds that Viewer observation to its declared manual check. Any arbitrary nonblank string would satisfy both checks under the current implementation.

This contradicts the Build instruction's claim that "Attestations remain distinct from automated evidence" in the practical sense needed for multiple non-automated checks: they are distinguished from automated output, but not from each other.

### D. Verification attempts are destructively overwritten

`cmd_verify` stores evidence as `records[tid]`, first replacing it with a `running` object and later replacing it with the final result (`.claude/bin/plan:2558-2562`, `:2575-2580`). There is no attempt list or history.

Observed consequences in this session:

- the bare T5 rerun replaced the earlier successful T5 evidence and its attestation text with the current failed record;
- the successful T3 retry replaced the immediately preceding failed `supabase db reset` result, so the JSON evidence no longer contains that failure;
- historical context survives only incidentally in the committed Git version and the T5 handoff.

This makes failures and flaky retries hard to audit and makes accidental bare verification destructive to the most recent good record.

## Recommended coldsession changes

1. Make attestations check-specific, for example `--attest visual:1="..."` and `--attest manual:1="..."`, or accept a structured JSON receipt keyed by check hash/index.
2. Bind each attestation to the exact declared check text/hash and require one attestation for every non-automated check. Never treat an arbitrary shared nonblank string as proof for all checks.
3. If required attestations are absent, fail before running automated commands or replacing prior evidence. Print the missing check kinds/text and the exact accepted syntax.
4. Preserve an append-only `attempts` history, or archive the prior record before replacing `records[tid]`. Keep a separate pointer to the latest successful current evidence.
5. Use task-scoped specification hashes. A task's evidence should be invalidated by changes to its own contract, Verify lines, files/reads, or transitive dependency contracts—not by unrelated later-task planning edits.
6. Keep working-file fingerprints as a separate invalidation dimension. In this incident, T5 should still be stale because T6 modified a file T5 owns, while T1-T4 should remain current.
7. Emit specific failure reasons (`automated_failed`, `missing_attestation`, `spec_changed`, `inputs_changed`) instead of the current combined message.

## Minimal reproduction for developers

Use a phase task with one automated Verify line, one visual line, and one manual line.

1. Run `plan verify <task>` without `--attest`: automated checks run, both non-automated results become `exit: null`, and prior evidence is overwritten.
2. Perform only the visual check, then run `plan verify <task> --attest "visual observation only"`: the same text is copied into both visual and manual results, both receive exit 0, and the task succeeds.
3. Change only a later unrelated task's `reads` entry and approve the new revision: the phase-wide spec hash changes, and verification of the original task requires its dependency chain to be reverified.

Step 2 should be tested in an isolated fixture rather than against this repository because it intentionally demonstrates a false attestation success.
