---
id: AP-201
title: Controlled QA corpus assurance profile
type: AssuranceProfile
status: active
owner: qa-corpus-maintainers
profile_kind: general
scope: corpus inventory, fixtures, controls, labels, bounds, and independent readers
impact_assessments:
  - id: impact-unrepresented-cell
    scenario: the corpus credits a detector without a discriminating case or silently omits a mode-language cell
    severity: material
relationships: []
review_policy:
  mode: require
  operations: [spec-review]
---

# Controlled QA corpus assurance profile

## Decision Boundary

This profile governs the corpus inventory, static inputs, expectations, healthy
controls, labels, bounds matrix, and the Python/Rust readers that grade it.

Apply it to any change that adds, removes, reclassifies, or reinterprets a case.
The corpus is recursively assurance-critical because Quire and Quoin use it to
claim their own detectors and metrics work.
Follow the case-before-fix procedure in `CONTRIBUTING.md`.

## Impact Scenarios

The corpus is the evidence producer for claims made about the QA tools, so a
defect in it has material impact across Quire and Quoin measurements.

`impact-unrepresented-cell`: a benchmark reports strong recall while an
unrepresented language or non-firing control is assumed working. Tool quality is
overstated and release work is misprioritized. Results can be invalidated and
rerun after repairing the corpus, but every engine and report scored against the
affected corpus revision is affected, and the defect is hard to see unless
bounds, controls, and reader parity are checked. Recovery is to fix the case or
inventory, rerun both readers, and publish a corrected record.

Seeded cases establish bounded behavior, not real-repository prevalence.

Prioritize explicit GAPs, discriminating controls, case-before-fix behavior,
language coverage, oracle independence, mutation validity, stable provenance,
and parity between the two authoritative readers.

Corpus changes can alter both ground truth and the population used to score
tools, which is why review is required.

## Evidence Policy

Review runs the evidence, integrity, and scope-boundary analyses over the change. Run `make ci`, including schema and parity self-tests. Require every failure
case to name a control and differ through its declared witness channel. Treat
new metadata as one canonical inventory contract consumed by both readers.

Retain the complete case inventory, derived gap and pending counts,
differential failures, label changes, and exact mutation/self-test output.

The Python and Rust readers are intentionally independent implementations over
the same static data. Agreement is necessary but not sufficient: labels and
oracles still require human review, and copied implementation logic is not an
independent oracle.

## Exceptions

A mode-language cell with no valid case is `GAP`, never assumed working. A
pending case that begins passing must be reconciled before the corpus can pass.
Changing ground truth requires explicit review and invalidates comparisons that
used the prior definition.
