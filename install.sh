#!/usr/bin/env bash
# Install the planning workflow into the current project.
#   ./install.sh [target-dir] [--keep]   default target: $PWD
#
# The documented flow clones this repo into the project as .coldsession and
# runs it from there, so nothing has to live outside the project:
#
#   cd ~/my-project
#   git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
#   .coldsession/install.sh
#
# When this script is that clone -- $DEST/.coldsession -- it deletes itself
# once the install is done. A checkout you keep somewhere else is never
# touched, and --keep skips the cleanup either way.
set -euo pipefail

KEEP=0
DEST=""
for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=1 ;;
    -*) echo "unknown option: $arg" >&2; exit 1 ;;
    *) DEST="$arg" ;;
  esac
done

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$(cd "${DEST:-$PWD}" && pwd)"

if [ "$SRC" = "$DEST" ]; then
  echo "refusing to install into the workflow repo itself" >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$DEST/.claude/commands" "$DEST/.claude/bin" "$DEST/docs/plans"

cp "$SRC"/commands/*.md "$DEST/.claude/commands/"
cp "$SRC/bin/plan" "$DEST/.claude/bin/plan"
chmod +x "$DEST/.claude/bin/plan"

# Ship the Windows entry point too, so a repo installed here still works for a
# teammate on Windows. The commands installed by this script call the POSIX
# `plan`; a Windows teammate re-runs install.ps1, which repoints them.
cp "$SRC/bin/plan.cmd" "$DEST/.claude/bin/plan.cmd"

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
    "allow": [
      "Bash(.claude/bin/plan:*)",
      "Bash(.claude/bin/plan.cmd:*)"
    ]
  }
}
JSON
  echo "wrote .claude/settings.json"
else
  echo "kept existing .claude/settings.json — add this yourself:"
  echo '  "model": "opusplan"'
  echo '  "permissions": { "allow": ["Bash(.claude/bin/plan:*)", "Bash(.claude/bin/plan.cmd:*)"] }'
fi

echo
echo "installed into $DEST"
echo "  .claude/commands/     10 commands, calling .claude/bin/plan"
echo "  .claude/bin/plan      dependency + context tool"
echo "  .claude/bin/plan.cmd  the same tool, for teammates on Windows"
echo "  templates/            PLAN.md, phase.md"
echo
echo "next: claude, then /define <your idea>"

# Clean up the throwaway clone. Only $DEST/.coldsession qualifies: a clone
# under another name, or a checkout outside the project, is something you
# chose to keep, and this script does not get to decide otherwise.
if [ "$SRC" = "$DEST/.coldsession" ]; then
  case "$KEEP" in
    1) echo; echo "kept $SRC (--keep)" ;;
    *)
      echo
      echo "removing $SRC"
      cd "$DEST"
      # exec, so the shell is replaced before the file it is reading goes away
      exec rm -rf "$SRC"
      ;;
  esac
elif [ "${SRC#"$DEST"/}" != "$SRC" ]; then
  echo
  echo "note: $SRC is inside the project; remove it when you're done"
fi
