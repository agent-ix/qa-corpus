---
id: SR-16440
title: "Code review of PLAT-847 marker-only corpus rework (qa-corpus PR 49)"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus; cases/**, corpus.yaml, modules/ecosystem/spec-artifacts-process/manifest.yaml, baselines/quire-rs.json, baselines/quoin.json, src/verify.rs, README.md (PR 49 diff vs origin/main only, head a37b2d6)"
review_set: subset
---

## Summary

Ticket: PLAT-847. PR head `a37b2d6`. This is a read-only review of the qa-corpus diff. It is the companion of quire-rs PR 627, which implements CR-215. The Rust lane (`src/verify.rs`) is folded into this file.

The Rust change is small and correct. It removes `binding_census.self_named` from `REQUIRED_CAPABILITIES` and drops the `self_named*` keys from census grading. No expectation file still uses those keys.

The module copy now has no `trace_tags.legacy` block. The `markers` and `implements` lists are unchanged apart from comment text. quire-rs PR 627 says a module that still declares `legacy` now fails to load, so the block had to go.

The derived counts agree with the tree. The fixtures fall from 199 to 196: five deleted fixtures, two added. The pairs fall from 92 to 91, and the controlled failures from 91 to 90. In `baselines/quire-rs.json`, findable rust detection failures fall by one, which matches the quire-rs ratchet's `score()` population rule. `corpus.yaml` drops `marker-form-mismatch` and `tag-on-non-binding-symbol` and adds `trace-id-outside-marker`. Its inventory and out-of-scope prose for the `test-name-id-*` rows are updated to match.

Evidence:
- `cargo test`: 18 lib tests pass.
- `cargo run -- bounds --require-complete`: 196 fixtures, 112 cells, 88 covered, 24 out-of-scope, GAP 0.
- A static check matched every marker line in the 135 changed input files against the manifest's own marker regex for that language. No line failed.
- `make verify` was not run. It needs a quire built from quire-rs PR 627.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | `baselines/quoin.json` was hand-edited, not re-measured. Nothing in the ecosystem reads it, and it still has a detection/rust `marker-form-mismatch` row (population 1) for the deleted `self-name-form-mismatch` case. Delete the file, because it is an unread stored record. | baselines/quoin.json:93-363, baselines/quoin.json:669-703 |
| FND-002 | medium | The PR hand-edits a vendored copy of spec-artifacts-process, and no upstream spec-artifacts-process change exists, open or merged. The corpus passes against a declaration that exists nowhere upstream. The `spec-artifacts-iso` schema copy still declares `legacy`. Once quire-rs PR 627 lands, the real module fails to load until upstream drops the block. | modules/ecosystem/spec-artifacts-process/manifest.yaml:890, modules/ecosystem/spec-artifacts-iso/module-manifest.schema.json:1168 |
| FND-003 | medium | 8 fixtures still write the removed `Trace: TC-001` form: the python and typescript cells of `catch-all-headline` and `no-symbol-method-in-the-verification-column`, plus their controls. Under CR-215 they bind nothing, so `no-symbol-bound` now fires there but not in their rust siblings, which use markers. | cases/detection/catch-all-headline/python/input/src/test_coverage.py:2, cases/minting/no-symbol-method-in-the-verification-column/typescript/input/src/coverage.test.ts:2 |
| FND-004 | low | Header comments carry incidental id-shaped tokens, which the advisory can now report against the file's module: `FR-043-INV-1` in a file this PR touched, `FR-001` in `real-tests-zero-tags`, and `TC-1`/`TC-001` in the new near-miss pair's `//!` lines. This breaks the corpus's one-defect-per-fixture rule, the same lesson as the redaction note this PR removed from `tag-at-module-scope`. | cases/join/tag-names-undeclared-section/python/input/src/test_coverage.py:2, cases/disposition/real-tests-zero-tags/python/input/src/test_coverage.py:3, cases/detection/untracked-id-near-miss-control/input/src/lib.rs:1-2 |
| FND-005 | low | Some prose describes removed forms or the wrong control. The `join` headers say `python-comment-id`, `rust-doc-comment-id` and similar forms bind the tag. The `stale-name-correct-trace` header says `rust-test-name-id` mints `TC-999`. The `tag-on-non-test-function` control calls its absent assertion "vacuous today". The `tag-on-non-test-function` case says its control "writes it as a marker", but that control writes `Implements:`. | cases/join/tag-names-bare-fr/python/input/src/test_coverage.py:5, cases/detection/stale-name-correct-trace/rust/expect.yaml:8, cases/attachment/tag-on-non-test-function-control/rust/expect.yaml:22, cases/attachment/tag-on-non-test-function/case.yaml:28 |
| FND-006 | low | 22 rewritten python fixtures use `@pytest.mark.trace` with no `import pytest`. On main, 14 of 15 import it. The README says inputs are runnable by hand. Several also put a comment line between the decorator and `def`. | cases/attachment/tag-inside-string-literal/python/input/src/thing.py:4, cases/disposition/real-tests-zero-tags-control/python/input/src/test_coverage.py:8-9 |

## Verdict

Examined: every changed case and its input, the `corpus.yaml` reason and inventory edits, the module copy, both baselines, the README counts and `src/verify.rs`.

The marker rewrites are real markers in each language: Rust `#[trace("…")]` above `#[test]`, Python `@pytest.mark.trace("…")` on the `def`, and a TypeScript `trace("…")` call inside the registration body. Each carries the id its case is about: bare `FR-001`, `FR-001-INV-1`, unminted `TC-999`, or the minted row. The property each case tests is kept, except where SR-16441 says otherwise.

The deleted cases test only removed machinery:
- `test-name-id-in-call-title` tested the `typescript-test-name-id` form.
- `self-name-form-mismatch` tested `marker-form-mismatch` and the `self_named` census.
- `test-name-id-in-fn-name` tested `id_format` padding. It is re-expressed as `untracked-id-near-miss`, which still tests the live #307 behaviour, with both present and absent assertions.

The `quire-rs.json` regeneration is consistent with the tree. The `quoin.json` label-only edit is not acceptable (FND-001).

Not mergeable until the medium findings are fixed and `make verify` passes against the quire-rs PR 627 head. It should land together with quire-rs PR 627.

## Dispositions

Round 1, checked against fix head `8d24c93`. Evidence for this round:
- qa-corpus `cargo test`: 18 tests pass.
- `bounds --require-complete`: 216 fixtures, GAP 0. The derived tags read 216 fixtures, 101 pairs and 100 failures.
- quire-rs PR 627 head `2648663`, whose `corpus` submodule is at `8d24c93`: `cargo test --test it corpus` gives 35 passed, 0 failed. This includes `corpus_cases_hold`, `tc1028_a_failure_case_discriminates_from_its_control` and the recall ratchet.

| FND | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | - |
| FND-002 | deferred | Upstream spec-artifacts-process PR 131 has merged and drops `trace_tags.legacy`. The copy now matches upstream, and the landing dependency for quire-rs PR 627 is gone. The copy is still vendored, and so is the `spec-artifacts-iso` schema copy that still declares `legacy`. That copy predates this ticket and needs its own de-vendoring change, which the lead should raise. |
| FND-003 | fixed | - |
| FND-004 | fixed | - |
| FND-005 | still-open | Most of the stale prose is gone. Two kinds remain. First, `rust-doc-comment-id` is still named as the binding form in cases/join/tag-names-undeclared-section/rust/input/src/lib.rs:4 and in its expect.yaml at line 13. Second, "vacuous today" still appears in cases/attachment/tag-on-non-test-function-control/{python,rust,typescript}/expect.yaml:22 and in cases/attachment/tag-at-module-scope-control/{python,typescript}/expect.yaml near lines 58 and 63. The ticket has landed, so the check is live, not vacuous. |
| FND-006 | still-open | `import pytest` is now present in every python fixture that uses the marker. A comment line still sits between `@pytest.mark.trace(...)` and `def` in 4 files: real-tests-zero-tags-control/python lines 11 and 18, and tag-on-non-test-function and its control, python test_coverage.py:12. |
