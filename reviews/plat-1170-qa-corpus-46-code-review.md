---
id: SR-16382
title: "Code review of PLAT-1170 legacy-implements-form corpus cases (qa-corpus PR 46)"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus; modules/legacy-implements/manifest.yaml, cases/attachment/legacy-implements-form/**, cases/attachment/legacy-implements-form-control/**, corpus.yaml, baselines/quire-rs.json, README.md (PR 46 diff vs origin/main only)"
review_set: subset
---

## Summary

Ticket: PLAT-1170. PR head `4a3cc09`. Read-only review of the qa-corpus diff.

The new module declares one textual Rust implements form with no `syntax`, and one `rust_attribute` form with the template `#[implements({ids})]`. That is the trigger condition of FR-050-AC-62.

The failure/control pair has the same shape as the neighbouring `guarded-implements-partial-match` pair: same `kind`, `findable`, `control_for` and `grading_contract` fields, and the same L1-L3 required finding channel. The two differ only in the one authored line: `/// Implements: FR-001` against `#[implements("FR-001")]`. Both expect the same `coverage.implements` metric (1/1) and `backed: 0`. The failure case asserts the reason's presence, path, line and message, and the control asserts its absence.

The count bumps agree with the tree. Two new fixtures take fixtures 191 to 193. One new pair takes pairs 88 to 89. One new controlled failure takes failure and controlled-failure counts 87 to 88. One new findable rust attachment failure takes `baselines/quire-rs.json` attachment/rust L1-L3 reached and population from 6 to 7, with no misses.

`legacy-implements-form` was already in `emitted` on `main`. The new case is not in `inventory`, which matches how `range-in-trace-tag` and `marker-mismatch` are accounted.

Evidence:
- `cargo run -- bounds --require-complete` reports 193 fixtures, GAP 0.
- The qa-corpus lib tests pass (18).
- Against quire-rs PR 615 head `99268c4`, the quire-rs `corpus` test filter passes (34), including tc1026 and the recall baselines.

`make verify` was not run. No hash, pin, vendored file or tracking record was introduced.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | low | No findings (placeholder) | - |

## Verdict

Examined: the module manifest, the failure and control cases with their inputs and expectations, the `corpus.yaml` derived-count edits, the baseline edits and the README pair-count edits. Clean. Mergeable together with quire-rs PR 615. The submodule pointer there must stay at this head, or at the squash of it.
