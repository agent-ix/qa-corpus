---
id: AP-201
title: Controlled QA corpus assurance profile
type: AssuranceProfile
status: active
owner: qa-corpus-maintainers
scope: corpus inventory, fixtures, controls, labels, bounds, and independent readers
impact: material evidence-producer impact across Quire and Quoin measurements
impact_assessments:
  - concern: the corpus credits a detector without a discriminating case or silently omits a mode-language cell
    tier: material
    scenario: a benchmark reports strong recall while an unrepresented language or non-firing control is assumed working
    dimensions:
      consequence: tool quality is overstated and release work is misprioritized
      reversibility: results can be invalidated and rerun after repairing the corpus
      scope_of_effect: every engine and report scored against the affected corpus revision
      detectability: low unless bounds, controls, and reader parity are checked
      recovery: fix the case or inventory, rerun both readers, and publish a corrected record
    rationale: the corpus is the evidence producer for claims made about the QA tools
    uncertainty: seeded cases establish bounded behavior, not real-repository prevalence
review_selection:
  mode: require
  analyses: [evidence, integrity, scope-boundary]
  rationale: corpus changes can alter both ground truth and the population used to score tools
lifecycle: [development, review, release, maintenance]
relationships: []
---

# Controlled QA corpus assurance profile

## Purpose and Scope

This profile governs the corpus inventory, static inputs, expectations, healthy
controls, labels, bounds matrix, and the Python/Rust readers that grade it.

## Applicability and Impact

Apply it to any change that adds, removes, reclassifies, or reinterprets a case.
The corpus is recursively assurance-critical because Quire and Quoin use it to
claim their own detectors and metrics work.
Follow the case-before-fix and Tier-2 pin procedure in `CONTRIBUTING.md`.

## Assurance Concerns

Prioritize explicit GAPs, discriminating controls, case-before-fix behavior,
language coverage, oracle independence, mutation validity, stable provenance,
and parity between the two authoritative readers.

## Selected Practices

Run `make ci`, including schema and parity self-tests. Require every failure
case to name a control and differ through its declared witness channel. Treat
new metadata as one canonical inventory contract consumed by both readers.

## Evidence Expectations

Retain corpus revision, module-source digests, engine identity, complete case
inventory, derived gap and pending counts, differential failures, label changes,
and exact mutation/self-test output.

## Tool Reliance and Independence

The Python and Rust readers are intentionally independent implementations over
the same static data. Agreement is necessary but not sufficient: labels and
oracles still require human review, and copied implementation logic is not an
independent oracle.

## Exceptions and Escalation

A mode-language cell with no valid case is `GAP`, never assumed working. A
pending case that begins passing must be reconciled before the corpus can pass.
Changing ground truth requires explicit review and invalidates comparisons that
used the prior definition.
