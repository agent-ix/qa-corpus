#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production symbol shall call `dangerousEval`.
set -euo pipefail
if grep -rn "dangerousEval" src/; then
  echo "forbidden dangerousEval found" >&2
  exit 1
fi
