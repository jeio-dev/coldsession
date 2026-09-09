#!/usr/bin/env sh
# PreToolUse Edit|Write -- only a human sets `status: approved`.
#
# Deliberately trivial: the event JSON arrives on stdin and is forwarded
# untouched to `plan guard`, which owns every decision, carries the tests,
# and fails open. Nothing here should ever grow a rule of its own.
#
# The project root comes from this script's own location -- it is installed
# at .claude/hooks/ -- because a hook runs wherever Claude Code launches it.
# It is reached by changing directory rather than by exporting PLAN_ROOT: an
# absolute path written by one shell is not always a path the interpreter in
# another can resolve, and on Windows that mismatch fails silently open.
dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." 2>/dev/null && pwd) || exit 0
[ -f "$dir/.claude/bin/plan" ] || exit 0
cd -- "$dir" || exit 0
exec ./.claude/bin/plan guard write
