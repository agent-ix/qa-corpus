---
id: SR-201
title: "Base review of the retained assurance-chain baseline"
type: SpecReview
analysis: base
scope: "FR-201; compatibility/assurance-chain-baseline.json; verify_assurance_chain_baseline.py; qa-corpus #20"
review_set: subset
relationships:
  - target: "ix://agent-ix/qa-corpus/FR-201"
    type: reviews
---

## Summary

This focused QUOIN base review applies the completeness, clarity, consistency,
testability, traceability, feasibility, and necessity checks to the baseline
that Engineering Assurance FR-019-AC-4 depends on. All eight legacy consumers
are pinned to published main-history commits. Each driver and its observation
source is SHA-256 bound, and each structured observation retains both what the
source measured and what it did not report. The baseline expressly refuses to
silently equate the legacy `partial` token with Quoin `incomplete`.

## Findings

| ID | Severity | Summary | Refs | Escape Cause |
| --- | --- | --- | --- | --- |
| FND-201 | medium | Closed: the previously absent eight-consumer baseline now records one canonical repository identity, published revision, driver digest, observation-source digest, non-vacuous result, witness, and limitation per consumer. | FR-201-AC-1..AC-3; `compatibility/assurance-chain-baseline.json` | missing-requirement |
| FND-202 | medium | Closed: source verification proves every pin is an ancestor of published `origin/main`, re-hashes both source blobs, and finds each retained witness in the reviewed bytes. | FR-201-AC-2; `scripts/verify_assurance_chain_baseline.py` | correct-requirement-no-evidence |
| FND-203 | low | Closed: the offline self-test rejects missing and duplicate consumers, malformed digests, vacuous observations, and deletion of the semantic-gap declaration. | FR-201-AC-4; `scripts/verify_assurance_chain_baseline.py --self-test` | correct-requirement-no-evidence |

## Criterion review

- **Complete and necessary:** the manifest carries exactly the facts required
  to preserve the pre-migration comparison surface; it does not copy a driver
  or assign implementation authority to the corpus.
- **Clear and atomic:** structure, publication reachability, byte identity,
  observation content, and mutation behavior are separate criteria.
- **Consistent and feasible:** all eight revisions were verified as published
  ancestors and all sixteen source digests plus every textual witness matched.
- **Testable and traced:** each criterion names the verifier mode that enforces
  it, and the Make targets keep offline and source-population checks distinct.

## Review disposition

**PASS.** The baseline is sufficient to precede Engineering Assurance TASK-024
implementation. It does not authorize consumer deletion; the Rust differential
and independent review still gate quire-research #60.
