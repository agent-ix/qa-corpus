---
id: FR-201
title: "Retain the assurance-chain consumer baseline"
type: FR
relationships:
  - target: "ix://agent-ix/engineering-assurance/FR-019"
    type: "supports"
---

# FR-201: Retain the assurance-chain consumer baseline

## Description

QA Corpus SHALL retain the published source identity and observed behavior of
each legacy Engineering Assurance chain consumer before replacement begins.

## Inputs

- The eight canonical consumer repositories named by Engineering Assurance
  FR-019.
- One published commit containing each `scripts/assurance_chain.py` driver.
- One review artifact at the same commit that records a non-vacuous successful
  observation of that driver.

## Outputs

- `compatibility/assurance-chain-baseline.json`, containing exact revisions,
  SHA-256 source digests, structured observations, witnesses, and limitations.
- A fail-closed offline structure check and an explicit source-reachability
  check.

## Behavior

- The baseline verifier SHALL require each of the eight canonical repository
  identities exactly once.
- The source verifier SHALL require each revision to be an ancestor of the
  repository published `origin/main` history.
- The source verifier SHALL compare the driver and observation-source bytes to
  their recorded SHA-256 digests.
- The source verifier SHALL require every retained witness to occur in the
  digest-matched observation source.
- The offline verifier SHALL reject an empty or unmatched observation.
- The baseline SHALL state each observation limitation instead of inferring a
  missing count or state spelling.
- The baseline SHALL preserve the unresolved distinction between a legacy
  `partial` state and a Quoin-owned `incomplete` outcome.

## Constraints

| ID | Constraint | Type | Validation |
| --- | --- | --- | --- |
| FR-201-CON-1 | QA Corpus SHALL treat retained scripts and reviews as evidence references rather than implementation authority. | Responsibility | Inspection |
| FR-201-CON-2 | Baseline capture SHALL NOT write a consumer repository or execute a producer. | Integrity | Test |

## Acceptance Criteria

| ID | Criteria | Verification |
| --- | --- | --- |
| FR-201-AC-1 | The baseline contains exactly the eight required repositories, each with one exact revision and two SHA-256 source digests. | Test (`verify_assurance_chain_baseline.py`) |
| FR-201-AC-2 | Every recorded revision is published on its repository main history, both source digests match, and every witness occurs in the recorded review bytes. | Test (`verify_assurance_chain_baseline.py --source-root`) |
| FR-201-AC-3 | Every consumer retains a non-vacuous matched observation and explicit limitations; the aggregate enumerates every legacy comparison state and calls out the unresolved `partial`/`incomplete` distinction. | Test (`verify_assurance_chain_baseline.py`) |
| FR-201-AC-4 | Removing or duplicating a consumer, corrupting a digest, emptying an observation, or deleting the semantic-gap statement fails the self-test. | Test (`verify_assurance_chain_baseline.py --self-test`) |

## Dependencies

- **Upstream**: `ix://agent-ix/engineering-assurance/FR-019` defines the
  differential behavior this corpus preserves.
- **Downstream**: `ix://agent-ix/engineering-assurance/TASK-024` consumes this
  baseline before `ix://agent-ix/quire-research/60` removes a legacy driver.
