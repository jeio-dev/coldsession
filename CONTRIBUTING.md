# Contributing

Run `python -m unittest discover -s tests -q` on Windows and Linux before release.
The CI matrix covers both operating systems and supported Python versions.
There are no third-party runtime dependencies. Bash installer tests on Windows
use Git Bash and forward-slash script paths, not the WSL launcher.

`bin/plan` owns document parsing, state transitions, scope checks, and evidence.
`bin/cs_install.py` owns both installers' preview, ownership, migration, apply,
validation, and rollback behavior. Keep the shell/PowerShell entry points thin.
Do not introduce application-code changes or execute project verification from
an installer. Stage first, back up all affected paths, recheck preview inputs,
and retain the upgrade journal until validation or restoration completes.

The repository lock spans the read and write and is shared with upgrades.
Unavailable locks refuse mutation. Never break a lock based only on age.
Workflow claims and process locks are distinct and need explicit recovery.
Use atomic replacements and journaled transactions for shared multi-file state.
Tests should exercise interrupted writes, recovery replay, and conflicting edits.

`plan guard` is quiet for unrelated projects and has no mandatory PLAN.md.
Format-2 mutations in a workflow must fail with actionable errors if state
cannot be validated. `plan metrics` is human-invoked and reports an empty
repository. These output contracts serve different callers.

Hook configuration is not proof of active hook trust. Preserve native sandbox,
permissions, models, unrelated hooks, and user settings. Document unsupported
paths in doctor and README. The normalized guard handles Claude and Codex
payloads; retain parity tests for files, patches, shells, traversal, symlinks,
and Windows junctions. Never dump environments or persist unbounded raw output.

Project policy skills belong to the host project. No installer may create or
remove `policy-*` skills. Commands must identify both harnesses' policy locations.
Canonical command names and Codex skill adapters remain in parity.

For a document-format change, register an explicit migration and preserve
historical closed phases. Do not merely bump workflow-rev. Never reinterpret
legacy readable scope as writable authorization or fabricate verification for
completed tasks. Preserve semantically unchanged approval. Changes to scope,
criteria, dependencies, constraints, or verification require renewed review.

The release version, phase format, templates, changelog, and installation pins
are tested separately. Existing project-local installations change only through
explicit preview/apply. Keep customizations and report conflicts.

Prompt wording needs behavioral validation. Use the opt-in, budgeted runners in
`evals/README.md`; include failed runs and unknown measurements. Deterministic
tests do not establish that a prompt saves tokens or improves quality. Never
claim improvements without live comparison evidence.

One agent is the default. Teams require explicit invocation. Coordinators own
shared state and commits; workers return assignment-bound results. Quiet workers
are never automatically replaced. Orca remains optional, and tests strip all
ambient session and orchestration identities before invoking it.
