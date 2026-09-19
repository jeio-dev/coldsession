---
description: Capture one small change as a GitHub issue without approving implementation
argument-hint: [--draft] <change request>
---

Create one coherent GitHub backlog issue from `$ARGUMENTS`. `--draft` prints the
proposed title and body without publishing. If no change request remains, ask
for a short description and stop. An issue can track several edits only when
they serve one observable outcome; split unrelated requests into separate
invocations.

## Establish the contract

Identify the repository and relevant durable state. Read AGENTS.md, PLAN.md
when present, relevant phase documents, and only the architecture, product
rules, and source files needed to check the claim. If PLAN.md exists, do not
read OBJECTIVE.md; the current plan and phase Constraints carry product scope.
If PLAN.md does not exist, read OBJECTIVE.md when present. During an active
Build claim, respect its bounded read scope; label unverified context instead
of reaching outside the task brief.
Use targeted searches and cite repository paths. Distinguish verified current
behavior from the user's report and from an untested hypothesis. Do not call a
document authoritative unless the repository establishes that authority. If a
rule or source conflicts with the request, ask only the blocking questions
before publishing, as one numbered round: every question asked together, each
with its recommended answer, then stop and wait. Do not invent missing
behavior or file paths.
Scout (experimental): when orientation would need more than about 5 files, run
`.claude/bin/plan scout status` first, and only if it exits 0, follow what it prints.

Check for a substantially duplicate open issue with
`gh issue list --repo <owner/repo> --state open --search <keywords> --json number,title,url,body`
when GitHub is available. If one exists, report its link and the overlap; do
not create a second issue. If this check fails, return a draft rather than
publishing blind.
If the request overlaps an active or approved phase, name that overlap in the
issue. Do not change the phase or imply that the issue amends its contract.

## Write the issue

Use an imperative, specific title and this compact body. Omit optional
sections that add no information, but keep Goal, Expected behavior, Acceptance
criteria, and Planning status. Avoid a numbered implementation plan: task
ordering, writable paths, and verification belong to `/cs-plan` or `/cs-revise`
after scope is settled.

    ## Goal
    <One observable outcome and who benefits.>

    ## Current state
    <What was observed, where, and at what revision if known. Label an
    unverified report as reported. Link relevant existing behavior or docs.>

    ## Expected behavior
    <The user-visible or operational behavior, including meaningful edge cases.>

    ## Acceptance criteria
    - [ ] <Observable result or named check.>

    ## Scope and references
    <Relevant in-scope boundary, explicit exclusion if needed, source-of-truth
    document links, and any related phase or issue. Use working GitHub links
    for cited files when the remote is known. Preserve the authority of linked
    rules instead of restating formulas or other volatile details.>

    ## Planning status
    Proposed backlog item for tracking only. This issue does not approve
    implementation or create a coldsession phase task. Incorporate it through
    new phase planning (`cs-plan --issue <number>`) or explicit replan, then
    review and human approval before Build.

Add a short `## Open decision` only if a nonblocking choice can be deferred to
planning. A blocking choice must be resolved before publishing. Mention likely
touchpoints only when verified and helpful; label any approach as a candidate,
not an instruction. Keep acceptance criteria about results rather than a
particular implementation unless the implementation is itself a requirement.

## Publish or hand back the draft

If `--draft` was supplied, print the complete title and body and stop. Otherwise
resolve the GitHub repository from the current checkout with
`gh repo view --json nameWithOwner,url`, then publish to that explicit repository
with `gh issue create --repo <owner/repo> --title <title> --body-file <file>`.
Use the exact drafted body in a temporary file and remove it whether the command
succeeds or fails.
Invoking this command authorizes creation of this one issue. Do not create
labels, milestones, branches, plan files, commits, or implementation changes.
If `gh` is unavailable, authentication fails, or the repository is ambiguous,
print the complete draft and the specific obstacle; do not claim an issue was
created. After success, print the issue URL, title, and the sentence that it is
tracking only. Do not call `.claude/bin/plan recommend`: an issue does not
advance phase state. When the user is ready to plan it, the path is
`/cs-plan --issue <number>` in a new session once the current phase is closed.
