---
id: SR-003
title: "Gap analysis — STD-227 Rust corpus runner"
type: SpecReview
analysis: gap-analysis
scope: "qa-corpus; assurance/AP-201-controlled-corpus.md, assurance/MP-201-gap-count.md, assurance/MP-202-detection-recall.md, src/*.rs, Makefile"
review_set: subset
---

## Summary

Compared the new Rust gates and tests with the controlled-corpus assurance plan and both measurement plans. The repository's active module set declares no obligations source, so the computed matrix cannot establish criterion coverage; direct trace tags and the changed behavior were inspected instead.

## Verdict

**CONDITIONAL** — the recorded test gap is closed on this PR; computed matrix coverage remains unavailable for this module.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | The replacement schema selftest lacks a behavioral check that an unknown declared field type is rejected. A typo in `corpus.yaml` can therefore weaken admission while `make ci` stays green. | Makefile:49; src/corpus.rs:1204 |

## Coverage

`quoin matrix --repo . --json` returned `no coverage_matrix criteria: the module declares no obligations: source`. Trace tags in the new unit tests name FR-065, MP-201, MP-202, and EA FR-011; this is a grep-level index, not computed matrix evidence. The changed source contains no `todo!`, `unimplemented!`, or unsafe block. The full live verdict comparison is pending the shared build lock.

Plan completion: not assessed

## Dispositions

| Finding | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | A focused test mutates the checked-in schema's `id` type and requires the real validator to refuse the checked-in case by name. |

## Re-review

The added test carries `Trace: FR-065-AC-1`, runs in `schema-selftest`, and fails if the declared type refusal is removed. No reverse gap or stub was introduced by the fix diff.
