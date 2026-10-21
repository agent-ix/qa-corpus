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

**CONDITIONAL** — the findings below need dispositions before the final gate.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | The measurement collection is assembled as `Value` with ad hoc string keys. A field omitted or misspelled in one branch still compiles, leaving a governed output malformed until a runtime consumer notices; use a typed `Serialize` output shape for the collection. | src/measurements.rs:430 |
| FND-002 | medium | `schema-selftest` now runs a small set of unit cases in place of the prior CLI mutation gate. For example, a change that silently accepts an unknown `case_schema.types` name can leave the target green because the replacement tests do not exercise that declared-type refusal. Add an end-to-end Rust mutation test for this contract. | Makefile:49; src/corpus.rs:1323 |

## Review evidence

The diff changes no CI workflow file. Focused checks on the reviewed head passed: 23 library tests, Clippy with warnings denied, formatting, `make bounds`, and `make external-channel`. The computed matrix reports no criteria because this module declares no obligations source; the separate gap analysis records that limitation. Live Python/Rust verdict parity and the final complete gate are pending the shared build lock.
