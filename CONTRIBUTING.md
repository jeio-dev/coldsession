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

`plan guard` and `plan metrics` must fail open. They run outside a
coldsession project — guard on every prompt and file tool call — so absent,
unreadable, or ambiguous plan state exits 0 in silence, and neither may go
through `read_phase(read_index())` in `main()` the way every other
subcommand does. If you touch either, re-run the fail-open tests and every
hook wrapper in a directory with no `PLAN.md`. A false positive on the happy
path is worse than a missing gate.

Every hook ships as an `.sh`/`.cmd` pair, ASCII-only, LF for the `.sh` and
CRLF for the `.cmd` per `.gitattributes`. A gate with only one half is a gate
that silently does not exist on the other install path. Changing the
generated `.claude/settings.json` means updating
`settings_is_generated_default` in both installers, which also decides
whether an uninstall may delete the file: it has to keep recognising every
earlier generated default so an upgrading user is never warned about a file
they did not touch.

Policy skills belong to the host project. coldsession ships no `policy-*`
skill and neither installer may ever create, list, or remove one: the removal
lists are `cs-*` and legacy `coldsession-*` only, and that is what makes the
convention safe to adopt. `commands/cs-plan.md` and `commands/cs-review.md`
are copied to Codex with only the runtime path patched, so anything they say
about where policy skills live has to name both `.claude/skills/` and
`.agents/skills/` rather than assume the Claude one.

`tests/test_plan.py` only exercises `bin/plan`; it cannot tell you whether a
reworded `commands/*.md` still does what it claims. If you change the prose
in `commands/`, `skills/`, or `templates/`, run `python evals/run.py` (needs
the `claude` CLI and live credentials -- see `evals/README.md`) against the
fixtures relevant to what you changed, in addition to the checklist above.

Changing the shape of the `tasks:` frontmatter is a phase-format change. Bump
`FORMAT_VERSION`, teach the linter exactly which older majors remain readable,
and document it in CHANGELOG.md. `TOOL_VERSION` tracks product releases and
can advance independently.
