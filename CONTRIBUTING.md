# Contributing

The commands are the product. `docs/universal-planning-workflow.html`
explains them; if you change a command, change the doc in the same PR.

Before opening a PR:

```bash
python3 -c "import ast; ast.parse(open('bin/plan').read())"
rm -rf /tmp/coldsession-check && mkdir -p /tmp/coldsession-check
./install.sh /tmp/coldsession-check
cd /tmp/coldsession-check \
  && cp templates/PLAN.md . \
  && sed -i 's|docs/plans/01-<slug>.md|docs/plans/01-x.md|' PLAN.md \
  && cp templates/phase.md docs/plans/01-x.md \
  && .claude/bin/plan lint
```

The shipped templates must pass their own linter. That is the whole test
suite; keep it that way or add a real one.

Changing the shape of the `tasks:` frontmatter is a breaking change. Every
installed project carries its own copy of the tool and its own phase files, so
there is no central migration. Bump the major version and say so in
CHANGELOG.md.
