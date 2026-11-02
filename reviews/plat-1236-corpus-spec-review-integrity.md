---
id: SR-005
title: "PLAT-1236 corpus spec-review/integrity review"
type: SpecReview
analysis: integrity
scope: "agent-ix/qa-corpus; PR 41; PLAT-1236; README.md; corpus.yaml; withdrawn-verification case, control and module"
review_set: subset
---

## Summary

Effective fixture/population counts are consistent; the newly nonempty pending class contradicts the adjacent historical comments.

## Assurance Context

AP-201 (assurance/AP-201-controlled-corpus.md) applies to added inventory, fixture and control data, with material evidence-producer impact. Its selected evidence, integrity and scope-boundary analyses were run. Case-before-fix evidence and the bounded control were inspected. Final complete corpus gates, candidate fixed-engine execution and independent-reader parity are unavailable at this pending-bank stage. No active exception was identified. The review does not treat agreement between the authored expectations and one engine as global tool qualification.

## Examined Units

- **AP-201** (examined), assurance/AP-201-controlled-corpus.md: Apply it to any change that adds, removes, reclassifies, or reinterprets a case. Follow the case-before-fix procedure in CONTRIBUTING.md.
- **withdrawn-verification** (examined), cases/minting/withdrawn-verification/case.yaml: Explicit Withdrawn verification cells retire only their own rows. The declaration parses, but reconciliation still counts the withdrawn tombstone as active and unbacked.
- **withdrawn-verification-control** (examined), cases/minting/withdrawn-verification-control/case.yaml: The control removes only that row and retains both the live and Planned siblings.
- **corpus.yaml** (examined), corpus.yaml: No fixture currently predicts a ticket that changes what mints.

## Evidence

Reviewed frozen head aaf371962859d3445fa20cdfe1cbfac89ec33188 against bcb2045. YAML parse and git diff --check passed. Independent static discovery reproduces 187 effective fixtures, 85 failure fixtures and 86 control pairs, matching the derived markers. Parser-only baseline log at /home/peter/dev/qualification-logs/titan-plat1236/parser-only-baseline.log records total/unbacked 3 for the failure and 2 for the control, with forward assertions failing on the expected count and extra FR-038-AC-92. No Cargo, full corpus gate, green forward run or pending promotion was performed by this reviewer. quoin advise was attempted but cannot derive obligations because this data repository has no spec/ document root; no advisor or computed-matrix coverage claim is made.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | low | The comments immediately above behaviour_change_tickets still say the class is EMPTY and no fixture predicts a minting change, while the PR adds the PLAT-1236 pending behavior-change fixture and a nonempty list. Update this explanation to describe the newly banked transition. | corpus.yaml:364-379 |

## Verdict

CONDITIONAL — fix the recorded finding before merge.
