#!/usr/bin/env bash
set -euo pipefail

pattern='#{8,}PATH_TO_[A-Z0-9_]+#{8,}'

if command -v rg >/dev/null 2>&1; then
  matches=$(rg -n "$pattern" scripts || true)
else
  matches=$(grep -R -n -E "$pattern" scripts || true)
fi

if [[ -n "$matches" ]]; then
  echo "[ERROR] Found unresolved script path placeholders:"
  echo
  echo "$matches"
  echo
  echo "Please replace all placeholders before running scripts."
  exit 1
fi

echo "[OK] No unresolved path placeholders found under scripts/."
