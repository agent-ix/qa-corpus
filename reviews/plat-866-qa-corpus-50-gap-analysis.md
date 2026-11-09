---
id: SR-20261103118148
title: "Gap analysis of PLAT-866 structural implements reasons (qa-corpus PR 50)"
type: SpecReview
analysis: gap-analysis
scope: "agent-ix/qa-corpus; cases/attachment/implements-syntax-unattached*/**, cases/attachment/partial-implements-syntax-match*/**, corpus.yaml (PR 50 diff vs origin/main only, head 405b101)"
review_set: subset
---

## Summary

Ticket: PLAT-866. Plan completion: not assessed.

qa-corpus has no `spec/` tree, so `quoin matrix` has nothing to read. This gap analysis is therefore a manual check of the reasons the diff declares against the quire-rs PR 630 criteria that define them (`spec/functional/FR-062-implements-relation.md`, at `0d94218`). The question is whether each declared reason has a failure and control pair in every language the declaration names.

The units examined:
- FR-062-AC-24 defines `implements-syntax-unattached`, for TypeScript wrappers only. It is witnessed by `implements-syntax-unattached`/typescript and its control, which cover the bare-statement variant.
- FR-062-AC-25 defines `partial-implements-syntax-match` for a decorator or wrapper candidate, in Python and TypeScript. It is witnessed by `partial-implements-syntax-match`/python and its control.
- FR-062-AC-19 is context only, as the AC the partial pair currently cites (see SR-20261103118147 FND-003).

Evidence: `make verify` with a quire built against quire-rs PR 630 passes all four new cases. `bounds --require-complete` reports GAP 0.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | low | `corpus.yaml` declares `partial-implements-syntax-match` for "a Python or TypeScript declaration", and FR-062-AC-25 covers wrapper candidates. Only a Python decorator fixture witnesses the reason. No TypeScript case, such as a partial match of a `typescript_wrapper` callee, exists. | corpus.yaml:270-272, cases/attachment/partial-implements-syntax-match/python/expect.yaml:1 |

## Verdict

FR-062-AC-24 is witnessed in its only language. The corpus witnesses a reason, not every engine branch: the other four unattached variants (argument, default export, non-chain argument, non-chain declarator) belong to quire-rs TC-2206, so their absence here is not a gap. FR-062-AC-25 is witnessed in Python only (FND-001). No production code outside fixtures changed.

## Dispositions

Round 1, checked against fix head `6088a96`. The new pair `partial-implements-syntax-match-wrapper`/typescript and its control witness FR-062-AC-25 for a `typescript_wrapper` candidate:
- The failure `const w = t.implementing("FR-001")(() => 1);` yields one `partial-implements-syntax-match` at `src/lib.ts:1` naming `t.implementing("FR-001")` on `w`, with `coverage.implements` matched 0.
- The control `ixTrace.implementing("FR-001")` binds `w` to FR-001, with matched 1 and no finding.
- `make verify` against quire-rs PR 630 at `7605461` gives 211/211 cases and 0 mismatches.

| FND | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | - |
