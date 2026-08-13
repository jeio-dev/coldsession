#!/usr/bin/env bash
# Update an existing install of the planning workflow to this checkout's version.
#   ./update.sh [target-dir] [--keep]   default target: $PWD
#
# Re-copies commands/*.md, bin/plan, and bin/plan.cmd over an existing
# .claude/ install -- the same files install.sh writes unconditionally.
# templates/ and .claude/settings.json are yours once installed, so this
# script never touches them; re-run install.sh if you want those refreshed
# too. Refuses a target with no existing install.
#
#   cd ~/my-project
#   git clone --depth 1 https://github.com/jeio-dev/coldsession.git .coldsession
#   .coldsession/update.sh
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
  echo "refusing to update the workflow repo itself" >&2
  exit 1
fi

if [ ! -f "$DEST/.claude/bin/plan" ]; then
  echo "no existing install found at $DEST/.claude/bin/plan -- run install.sh instead" >&2
  exit 1
fi

OLD_VERSION="$("$DEST/.claude/bin/plan" version 2>/dev/null || echo unknown)"

cp "$SRC"/commands/*.md "$DEST/.claude/commands/"
cp "$SRC/bin/plan" "$DEST/.claude/bin/plan"
chmod +x "$DEST/.claude/bin/plan"
cp "$SRC/bin/plan.cmd" "$DEST/.claude/bin/plan.cmd"

NEW_VERSION="$("$DEST/.claude/bin/plan" version 2>/dev/null || echo unknown)"

echo
echo "updated $DEST: $OLD_VERSION -> $NEW_VERSION"
echo "  .claude/commands/     10 commands"
echo "  .claude/bin/plan      dependency + context tool"
echo "  .claude/bin/plan.cmd  the same tool, for teammates on Windows"
echo
echo "templates/ and .claude/settings.json were left alone"
echo "next: git diff .claude, review, then commit"

# Same disposable-clone cleanup as install.sh. Only $DEST/.coldsession
# qualifies: a clone under another name, or a checkout outside the project,
# is something you chose to keep, and this script does not get to decide
# otherwise.
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
