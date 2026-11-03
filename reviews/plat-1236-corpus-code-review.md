---
id: SR-004
title: "PLAT-1236 corpus code-review review"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus; PR 41; PLAT-1236; README.md; corpus.yaml; withdrawn-verification case, control and module"
review_set: subset
---

## Summary

The pending case preserves the real tombstone, and the control differs only by its removal. A consuming metadata assertion is not satisfied by the new tracking tags.

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
| FND-001 | medium | Both new cases lack a TC-prefixed tracking tag, but the consuming quire-rs tc1021_the_vocabularies_come_from_the_corpus_not_from_this_file test asserts at least one TC- tag for every case (tests/corpus_cases.rs:474). The focused baseline does not exercise that test. Add the existing owning tracking tag for the pending/live grading protocol (TC-1023), retaining the new FR-050 criterion tags; do not invent retirement verification credit or weaken the metadata gate. | cases/minting/withdrawn-verification/case.yaml:13 |

## Verdict

CONDITIONAL — fix the recorded finding before merge.

## Dispositions

| FND | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | Both fixtures now retain the existing owning pending/live-protocol tracking id alongside the retirement criteria. The unchanged consumer metadata prefix assertion is satisfied. |

## Promotion inspection (disposition round 1)

Inspected head f2b83813e39d03096cd668ba5a7b8d816c735a34. The new failure and control documents are byte-identical after replacing only the failure row's Verification token `Withdrawn` with `Test`; the reason prose, all three IDs and both live siblings remain. The failure expects two live/unbacked rows, and its healthy control expects all three. This is a stronger retained-prose control against hardcoded identity/prose retirement inference. Both fixtures retain `TC-1023`, which truthfully tracks the existing corpus-wide pending/live expectation protocol; the FR-050 criterion tags remain.

Promotion removed both `pending` metadata and its forward file and moved the measured forward expectation into the live block. The earlier parser-only baseline/control remain historical measurements; the updated case comments expressly distinguish them from this final control. The fixed-engine forward receipt `/tmp/plat1236-corpus-forward.log` records its focused assertion pass, but uses the earlier pending-stage control. No execution of the final three-row control or full QA gate was performed by this reviewer. Parent qualification of that final control remains a merge prerequisite. No new finding was identified in the promotion itself.

## Current verdict

All recorded findings are fixed. Final-control execution and final qualifying gates remain required before merge; no such run is claimed by this disposition.
