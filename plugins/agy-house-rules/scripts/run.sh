#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${AGY_PYTHON:-}" ]]; then
    exec "${AGY_PYTHON}" "${SCRIPT_DIR}/hook.py" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 "${SCRIPT_DIR}/hook.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "${SCRIPT_DIR}/hook.py" "$@"
else
    echo "house-rules error: python3 not found on PATH" >&2
    exit 1
fi
