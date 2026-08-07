#!/usr/bin/env bash
# Install the planning workflow into the current project.
#   ./install.sh [target-dir]   default: $PWD
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$PWD}"

if [ "$SRC" = "$DEST" ]; then
  echo "refusing to install into the workflow repo itself" >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$DEST/.claude/commands" "$DEST/.claude/bin" "$DEST/docs/plans"

cp "$SRC"/commands/*.md "$DEST/.claude/commands/"
cp "$SRC/bin/plan" "$DEST/.claude/bin/plan"
chmod +x "$DEST/.claude/bin/plan"

mkdir -p "$DEST/templates"
for t in PLAN.md phase.md; do
  [ -f "$DEST/templates/$t" ] || cp "$SRC/templates/$t" "$DEST/templates/$t"
done

SETTINGS="$DEST/.claude/settings.json"
if [ ! -f "$SETTINGS" ]; then
  cat > "$SETTINGS" <<'JSON'
{
  "model": "opusplan",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  },
  "permissions": {
    "allow": ["Bash(.claude/bin/plan:*)"]
  }
}
JSON
  echo "wrote .claude/settings.json"
else
  echo "kept existing .claude/settings.json — add this yourself:"
  echo '  "model": "opusplan"'
  echo '  "permissions": { "allow": ["Bash(.claude/bin/plan:*)"] }'
fi

echo
echo "installed into $DEST"
echo "  .claude/commands/   10 commands"
echo "  .claude/bin/plan    dependency + context tool"
echo "  templates/          PLAN.md, phase.md"
echo
echo "next: claude, then /define <your idea>"
