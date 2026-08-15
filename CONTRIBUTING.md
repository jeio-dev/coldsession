# Contributing

The commands are the product. `docs/universal-planning-workflow.html`
explains them; if you change a command, change the doc in the same PR.
The Codex skills are adapters around those commands, not a second copy of the
workflow. Keep each `skills/cs-*/SKILL.md` focused on argument and
invocation differences.

Before opening a PR:

```bash
python3 -c "import ast; ast.parse(open('bin/plan').read())"
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
Codex's `skill-creator` skill, and confirm an install contains ten `cs-*`
directories under `.agents/skills/` plus ten patched canonical commands under
`.agents/coldsession/commands/`.

The shipped templates must pass their own linter. That is the whole test
suite; keep it that way or add a real one.

Changing the shape of the `tasks:` frontmatter is a phase-format change. Bump
`FORMAT_VERSION`, teach the linter exactly which older majors remain readable,
and document it in CHANGELOG.md. `TOOL_VERSION` tracks product releases and
can advance independently.
