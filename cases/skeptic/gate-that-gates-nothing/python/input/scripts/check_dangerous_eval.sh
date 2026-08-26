#!/usr/bin/env bash
# Gate for FR-001-AC-1: no production symbol shall call `dangerous_eval`.
set -euo pipefail
grep -rn "dangerous_eval" src/ | wc -l
exit 0
