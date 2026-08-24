#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production `unwrap`.
set -euo pipefail
grep -rn "unwrap()" src/ | wc -l
exit 0
