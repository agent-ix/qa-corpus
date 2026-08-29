#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production symbol shall call `dangerousEval`.
set -euo pipefail
grep -rn "dangerousEval" src/ | wc -l
exit 0
