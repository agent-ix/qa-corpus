---
id: SR-002
title: "Code review — STD-227 Rust corpus runner"
type: SpecReview
analysis: code-review
scope: "qa-corpus; Cargo.toml, Makefile, src/*.rs, removed Python gates, README.md, CONTRIBUTING.md, corpus.yaml, compatibility/README.md"
review_set: subset
---

## Summary

Reviewed the Rust replacement of the active corpus readers, runner, reporting and measurement gates, compatibility check, and case scaffolder. The port preserves the authored fixture bytes and keeps the CI target names, but two assurance contracts need tightening before merge.

## Verdict

**CONDITIONAL** — both findings are fixed on this PR; live parity and the final gate remain pending.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | The measurement collection is assembled as `Value` with ad hoc string keys. A field omitted or misspelled in one branch still compiles, leaving a governed output malformed until a runtime consumer notices; use a typed `Serialize` output shape for the collection. | src/measurements.rs:430 |
| FND-002 | medium | `schema-selftest` now runs a small set of unit cases in place of the prior CLI mutation gate. For example, a change that silently accepts an unknown `case_schema.types` name can leave the target green because the replacement tests do not exercise that declared-type refusal. Add an end-to-end Rust mutation test for this contract. | Makefile:49; src/corpus.rs:1323 |

## Review evidence

The diff changes no CI workflow file. Focused checks before remediation passed: 23 library tests, Clippy with warnings denied, formatting, `make bounds`, and `make external-channel`. The targeted schema mutation test and six measurement tests pass after remediation, as do formatting and Clippy. The computed matrix reports no criteria because this module declares no obligations source; the separate gap analysis records that limitation. On the same checked-in fixtures and installed Quire/Quoin binaries, Python and Rust verifier logs were byte-identical: 174/174 detection cases, 85 graded pairs, zero mismatches, and 11/11 reporting cases with zero mismatches. Both exited zero. The final complete gate is pending the shared build lock.

## Dispositions

| Finding | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | `Collection`, `Scope`, and `Environment` now derive `Serialize`; construction names every required envelope field at compile time. Source-defined raw evidence remains dynamic by design. The existing collection ID and observation tests pass. |
| FND-002 | fixed | `unknown_declared_field_type_is_rejected` mutates the checked-in declaration's `id` type and exercises the real case validator on a checked-in case; `schema-selftest` invokes this test. |

## Re-review

The fix diff contains only the typed collection envelope, its serialization boundary, and the focused schema mutation test. Rust review checked the emitted field names against the previous JSON keys, test isolation, panics, lints, and the `Makefile` target; no new finding.
