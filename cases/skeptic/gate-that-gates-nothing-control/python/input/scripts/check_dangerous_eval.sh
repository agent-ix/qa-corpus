#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production symbol shall call `dangerous_eval`.
set -euo pipefail
if grep -rn "dangerous_eval" src/; then
  echo "forbidden dangerous_eval found" >&2
  exit 1
fi
