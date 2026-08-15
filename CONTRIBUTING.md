# Contributing

The commands are the product. `docs/universal-planning-workflow.html`
explains them; if you change a command, change the doc in the same PR.
The Codex skills are adapters around those commands, not a second copy of the
workflow. Keep each `skills/cs-*/SKILL.md` focused on argument and
invocation differences.

Before opening a PR:

```bash
python3 -c "import ast; ast.parse(open('bin/plan').read())"
python3 -m unittest discover -s tests -v
rm -rf /tmp/coldsession-check && mkdir -p /tmp/coldsession-check
./install.sh /tmp/coldsession-check --agent both
cd /tmp/coldsession-check \
  && cp templates/PLAN.md . \
  && sed -i 's|docs/plans/01-<slug>.md|docs/plans/01-x.md|' PLAN.md \
  && cp templates/phase.md docs/plans/01-x.md \
  && .claude/bin/plan lint \
  && .agents/coldsession/bin/plan lint
```

Also validate every Codex skill with the `quick_validate.py` shipped by
Codex's `skill-creator` skill, and confirm an install contains nine canonical
`cs-*` skills and commands plus the explicit-only `cs-recheck` compatibility
alias on both surfaces. Confirm the shared templates include `OBJECTIVE.md`,
`PLAN.md`, and `phase.md`.

The shipped phase template must pass its own linter. Runtime state transitions
belong in the standard-library unittest suite; keep it dependency-free.

Changing the shape of the `tasks:` frontmatter is a phase-format change. Bump
`FORMAT_VERSION`, teach the linter exactly which older majors remain readable,
and document it in CHANGELOG.md. `TOOL_VERSION` tracks product releases and
can advance independently.
