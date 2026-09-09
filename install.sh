#!/usr/bin/env bash
# Install, update, or switch coldsession agent integrations in a project.
#   ./install.sh [target-dir] [--agent claude|codex|both] [--keep]
set -euo pipefail

KEEP=0
DEST=""
AGENT=""

usage() {
  echo "usage: ./install.sh [target-dir] [--agent claude|codex|both] [--keep]" >&2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1 ;;
    --agent)
      [ "$#" -ge 2 ] || { echo "--agent requires a value" >&2; usage; exit 2; }
      AGENT="$2"
      shift
      ;;
    --agent=*) AGENT="${1#--agent=}" ;;
    -*) echo "unknown option: $1" >&2; usage; exit 2 ;;
    *)
      [ -z "$DEST" ] || { echo "only one target directory is allowed" >&2; usage; exit 2; }
      DEST="$1"
      ;;
  esac
  shift
done

case "$AGENT" in
  "")
    if [ ! -t 0 ]; then
      echo "--agent is required when input is not interactive" >&2
      usage
      exit 2
    fi
    echo "Install coldsession for:"
    echo "  1) Claude Code"
    echo "  2) Codex"
    echo "  3) Both"
    while :; do
      printf "Choose 1, 2, or 3: "
      IFS= read -r choice || { echo; echo "no selection received" >&2; exit 2; }
      case "$choice" in
        1|claude) AGENT="claude"; break ;;
        2|codex) AGENT="codex"; break ;;
        3|both) AGENT="both"; break ;;
        *) echo "enter 1, 2, or 3" >&2 ;;
      esac
    done
    ;;
  claude|codex|both) ;;
  *) echo "invalid agent: $AGENT" >&2; usage; exit 2 ;;
esac

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$(cd "${DEST:-$PWD}" && pwd)"

if [ "$SRC" = "$DEST" ]; then
  echo "refusing to install into the workflow repo itself" >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

version_at() {
  local path="$1"
  if [ -f "$path" ]; then
    python3 "$path" version 2>/dev/null || true
  fi
}

OLD_CLAUDE_VERSION="$(version_at "$DEST/.claude/bin/plan")"
OLD_CODEX_VERSION="$(version_at "$DEST/.agents/coldsession/bin/plan")"
KNOWN_INSTALL=0
if [ -n "$OLD_CLAUDE_VERSION" ] || [ -n "$OLD_CODEX_VERSION" ]; then
  KNOWN_INSTALL=1
fi
LEGACY_INSTALL=0
case "$OLD_CLAUDE_VERSION" in
  1.*) LEGACY_INSTALL=1 ;;
esac
NEW_VERSION="$(python3 "$SRC/bin/plan" version)"
REMOVED=0
SETTINGS_WARNING=0

remove_file() {
  if [ -f "$1" ]; then
    rm -f -- "$1"
    REMOVED=$((REMOVED + 1))
  fi
}

remove_dir() {
  if [ -d "$1" ]; then
    rm -rf -- "$1"
    REMOVED=$((REMOVED + 1))
  fi
}

# The wrappers this installer ships, and so the only files it will copy or
# remove: a project may keep hooks of its own in the same directory. One list
# for both operations, and the same list install.ps1 uses -- when the two
# installers disagreed about it, a project uninstalled from PowerShell lost a
# hook it kept when uninstalled from sh.
HOOK_PATTERNS=("cs-guard-*.sh" "cs-guard-*.cmd")

# The directory goes only if removing ours emptied it.
remove_hooks() {
  local dir="$1/.claude/hooks"
  [ -d "$dir" ] || return 0
  for pattern in "${HOOK_PATTERNS[@]}"; do
    for path in "$dir"/$pattern; do
      if [ -f "$path" ]; then
        remove_file "$path"
      fi
    done
  done
  rmdir "$dir" 2>/dev/null || true
}

# Exit 0 when settings.json is one this installer generated and nobody has
# touched. It decides both whether an uninstall may delete the file and
# whether an update may rewrite it, so it has to keep recognising the
# pre-hooks three-key default: a user upgrading from 2.2 never edited that
# file and must not be warned about it.
settings_is_generated_default() {
  python3 - "$1" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8-sig") as handle:
        actual = json.load(handle)
except (OSError, ValueError):
    raise SystemExit(1)

allowed_sets = (
    {
        "Bash(.claude/bin/plan:*)",
        "Bash(.claude/bin/plan.cmd:*)",
        "PowerShell(.claude/bin/plan.cmd:*)",
    },
    {"Bash(.claude/bin/plan:*)", "Bash(.claude/bin/plan.cmd:*)"},
)

# Hook wrappers ship as .sh/.cmd pairs, so the command is compared by name
# rather than by path: one install writes .sh, the other .cmd, and both are
# this installer's own output. The surrounding quotes come off first --
# write_settings quotes the executable path so a project directory with a
# space in it still launches, and this has to recognise what it writes.
expected_hooks = {
    "UserPromptSubmit": [(None, "cs-guard-stage")],
    "PreToolUse": [("Read|Edit|Write", "cs-guard-read"),
                   ("Edit|Write", "cs-guard-write")],
    "PostToolUse": [("Edit|Write", "cs-guard-lint")],
}


def signature(hooks):
    if not isinstance(hooks, dict):
        return None
    sig = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            return None
        rows = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - {"matcher", "hooks"}:
                return None
            specs = entry.get("hooks")
            if not isinstance(specs, list) or len(specs) != 1:
                return None
            spec = specs[0]
            if not isinstance(spec, dict) or spec.get("type") != "command":
                return None
            command = spec.get("command")
            if not isinstance(command, str):
                return None
            name = command.strip().strip('"').replace("\\", "/").rsplit("/", 1)[-1]
            for suffix in (".sh", ".cmd"):
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
            rows.append((entry.get("matcher"), name))
        sig[event] = rows
    return sig


keys = set(actual)
if keys not in ({"model", "env", "permissions"},
                {"model", "env", "permissions", "hooks"}):
    raise SystemExit(1)
if actual.get("model") != "opusplan":
    raise SystemExit(1)
if actual.get("env") != {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}:
    raise SystemExit(1)
permissions = actual.get("permissions")
if not isinstance(permissions, dict) or set(permissions) != {"allow"}:
    raise SystemExit(1)
allow = permissions.get("allow")
if not isinstance(allow, list) or set(allow) not in allowed_sets or len(allow) != len(set(allow)):
    raise SystemExit(1)
if "hooks" in keys and signature(actual["hooks"]) != expected_hooks:
    raise SystemExit(1)
PY
}

# True for the generated default written before hooks existed: still ours,
# still untouched, and one rewrite short of having the gates.
settings_predates_hooks() {
  python3 - "$1" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8-sig") as handle:
        actual = json.load(handle)
except (OSError, ValueError):
    raise SystemExit(1)
raise SystemExit(1 if "hooks" in actual else 0)
PY
}

legacy_commands=(approve build close define groundwork plan recheck review revise status)

if [ "$LEGACY_INSTALL" -eq 1 ]; then
  for name in "${legacy_commands[@]}"; do
    remove_file "$DEST/.claude/commands/$name.md"
  done
  for dir in "$DEST"/.agents/skills/coldsession-*; do
    [ -d "$dir" ] && remove_dir "$dir"
  done
fi

if [ "$AGENT" = "codex" ]; then
  if [ "$KNOWN_INSTALL" -eq 1 ]; then
    for path in "$DEST"/.claude/commands/cs-*.md; do
      [ -f "$path" ] && remove_file "$path"
    done
    remove_file "$DEST/.claude/bin/plan"
    remove_file "$DEST/.claude/bin/plan.cmd"
    remove_hooks "$DEST"
    if [ -f "$DEST/.claude/settings.json" ]; then
      if settings_is_generated_default "$DEST/.claude/settings.json"; then
        remove_file "$DEST/.claude/settings.json"
      else
        SETTINGS_WARNING=1
      fi
    fi
  fi
else
  if [ "$KNOWN_INSTALL" -eq 1 ]; then
    for path in "$DEST"/.claude/commands/cs-*.md; do
      [ -f "$path" ] && remove_file "$path"
    done
  fi
  remove_hooks "$DEST"
  mkdir -p "$DEST/.claude/commands" "$DEST/.claude/bin" "$DEST/.claude/hooks"
  cp "$SRC"/commands/cs-*.md "$DEST/.claude/commands/"
  cp "$SRC/bin/plan" "$DEST/.claude/bin/plan"
  chmod +x "$DEST/.claude/bin/plan"
  cp "$SRC/bin/plan.cmd" "$DEST/.claude/bin/plan.cmd"
  for pattern in "${HOOK_PATTERNS[@]}"; do
    cp "$SRC"/hooks/$pattern "$DEST/.claude/hooks/"
  done
  chmod +x "$DEST"/.claude/hooks/cs-guard-*.sh

  write_settings() {
    cat > "$1" <<'JSON'
{
  "model": "opusplan",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  },
  "permissions": {
    "allow": [
      "Bash(.claude/bin/plan:*)",
      "Bash(.claude/bin/plan.cmd:*)",
      "PowerShell(.claude/bin/plan.cmd:*)"
    ]
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-stage.sh\""
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-read.sh\""
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-write.sh\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/cs-guard-lint.sh\""
          }
        ]
      }
    ]
  }
}
JSON
  }

  SETTINGS="$DEST/.claude/settings.json"
  if [ ! -f "$SETTINGS" ]; then
    write_settings "$SETTINGS"
    echo "wrote .claude/settings.json"
  elif settings_is_generated_default "$SETTINGS" && settings_predates_hooks "$SETTINGS"; then
    # Untouched output of an installer that predates the gates. Rewriting it
    # is the only way an upgrade delivers them, and there is nothing of the
    # user's in there to lose.
    write_settings "$SETTINGS"
    echo "updated .claude/settings.json with the hook gates"
  else
    echo "kept existing .claude/settings.json"
  fi
fi

if [ "$AGENT" = "claude" ]; then
  if [ "$KNOWN_INSTALL" -eq 1 ]; then
    remove_dir "$DEST/.agents/coldsession"
    for dir in "$DEST"/.agents/skills/cs-*; do
      [ -d "$dir" ] && remove_dir "$dir"
    done
  fi
else
  if [ "$KNOWN_INSTALL" -eq 1 ]; then
    remove_dir "$DEST/.agents/coldsession"
    for dir in "$DEST"/.agents/skills/cs-*; do
      [ -d "$dir" ] && remove_dir "$dir"
    done
  fi
  mkdir -p "$DEST/.agents/skills" "$DEST/.agents/coldsession/commands" \
    "$DEST/.agents/coldsession/bin"
  cp -R "$SRC"/skills/cs-* "$DEST/.agents/skills/"
  for source in "$SRC"/commands/cs-*.md; do
    target="$DEST/.agents/coldsession/commands/$(basename "$source")"
    sed 's|\.claude/bin/plan|.agents/coldsession/bin/plan|g' "$source" > "$target"
  done
  cp "$SRC/bin/plan" "$DEST/.agents/coldsession/bin/plan"
  chmod +x "$DEST/.agents/coldsession/bin/plan"
  cp "$SRC/bin/plan.cmd" "$DEST/.agents/coldsession/bin/plan.cmd"
fi

mkdir -p "$DEST/docs/plans" "$DEST/templates"
for template in OBJECTIVE.md PLAN.md phase.md; do
  [ -f "$DEST/templates/$template" ] || cp "$SRC/templates/$template" "$DEST/templates/$template"
done

echo
if [ "$KNOWN_INSTALL" -eq 1 ]; then
  previous="${OLD_CLAUDE_VERSION:-none}/${OLD_CODEX_VERSION:-none}"
  echo "updated $DEST: $previous -> $NEW_VERSION"
else
  echo "installed coldsession $NEW_VERSION into $DEST"
fi
echo "  agents: $AGENT"
if [ "$AGENT" != "codex" ]; then
  echo "  Claude: .claude/commands/cs-*, .claude/bin/plan, .claude/hooks/cs-guard-*"
fi
if [ "$AGENT" != "claude" ]; then
  echo "  Codex:  .agents/skills/cs-* and .agents/coldsession/"
fi
echo "  shared: templates/ and docs/plans/"
[ "$REMOVED" -eq 0 ] || echo "  replaced/removed $REMOVED managed item(s)"
if [ "$SETTINGS_WARNING" -eq 1 ]; then
  echo "  kept modified .claude/settings.json; remove stale coldsession permissions manually"
fi
echo
case "$AGENT" in
  claude) echo "next: /cs-define <your idea>"; echo "review: git diff -- .claude templates" ;;
  codex) echo 'next: $cs-define <your idea>'; echo "review: git diff -- .agents templates" ;;
  both) echo "next: Claude Code /cs-define or Codex \$cs-define"; echo "review: git diff -- .claude .agents templates" ;;
esac

if [ "$SRC" = "$DEST/.coldsession" ]; then
  case "$KEEP" in
    1) echo; echo "kept $SRC (--keep)" ;;
    *)
      echo
      echo "removing $SRC"
      cd "$DEST"
      exec rm -rf -- "$SRC"
      ;;
  esac
elif [ "${SRC#"$DEST"/}" != "$SRC" ]; then
  echo
  echo "note: $SRC is inside the project; remove it when you're done"
fi
