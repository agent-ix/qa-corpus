#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production `unwrap`.
set -euo pipefail
if grep -rn "unwrap()" src/; then
  echo "forbidden unwrap found" >&2
  exit 1
fi
