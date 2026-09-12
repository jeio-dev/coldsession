#!/usr/bin/env bash
# Both installers use the same preview, ownership, migration, and rollback engine.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; assert sys.version_info >= (3, 9)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
[ -n "$PYTHON" ] || { echo "Python 3.9+ is required" >&2; exit 1; }
exec "$PYTHON" "$SRC/bin/cs_install.py" "$@"
