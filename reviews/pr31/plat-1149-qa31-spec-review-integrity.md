---
id: SR-011
title: PLAT-1149 QA PR 31 spec-review/integrity
type: SpecReview
analysis: integrity
scope: agent-ix/qa-corpus; PR 31; 63 expect.yaml paths listed below; PLAT-1149
review_set: subset
---

## Summary

Frozen QA candidate 3aa459624b3d93107191fa5bcb02bfcd0b95031a, compared with main 1bc93126d6c6d8c0f7947ac2a20ff20c5b3c44e5. Ticket: PLAT-1149. This is the single independent QA PR 31 review, separate from engine PR 515. No fixes, merges, branch commits or public findings were made.

## Assurance Context

AP-201 (assurance/AP-201-controlled-corpus.md) applies: 63 ground-truth expectations change, with material evidence-producer impact. Selected evidence, integrity and scope-boundary analyses accompany this code review. Independent review read the unchanged declarations and source files, rather than accepting engine output as the oracle. Existing complete/retired status, diagnostic, census, metric, group and count fields remain identical. No active exception was identified. Architecture/measurement qualification decisions and final independent-reader parity and complete aggregate gates are unavailable in this review; they remain lead-owned prerequisites, not claims inferred from the focused pass.

## Evidence

An independently derived git/YAML audit (independent-audit.json) proves exactly 63 changed expect.yaml paths and 72 appended exact unbacked rows, with every old row and all other AST values identical. Each appended row is independently declared under Acceptance Criteria, names its own AC identity, and retains the cited TC identity in target_ids. Reading every source file found no own-criterion claim for any added row. The only textual occurrences of an added criterion in source are six post-colon prose mentions in four TypeScript fixtures. The unchanged declared typescript-comment-id form captures the leading TC list and stops before the colon; those prose mentions cannot verify a criterion.

This distinction preserves aggregate semantics: TC rows can be backed by referenced evidence, while a criterion row needs its own verifies relation. Source fixtures are parser/binder seeds; their toy assertions are not credited as verification of the warning/declaration prose itself. The change neither blesses a newly observed literal/parser behavior nor repairs existing unrelated fixture prose.

Inspected case-before-expectation failure receipt ../focused-204d70e/corpus.log: fixed engine with old expectations reports the missing criterion rows at L2. Inspected ../qa31-current/corpus-focused.log: engine 04008ff with QA 3aa4596 passes corpus_cases_hold (1/1, exit 0). These are producer receipts, not a reviewer rerun or full gate. No Cargo, Kani, IEEE/proof suite or aggregate run was performed here. git diff --check passed. quire matrix --scope . --format json and quoin advise --json were attempted; both cannot operate at this corpus root because it has no spec/ document root. Manual fixture declaration/source/expectation inspection supplies the bounded acceptance check; no computed whole-repository coverage claim is made.

## Preservation and scope

The net PR tree changes only these 63 expectations. The non-force ancestry reconciliation is evaluated by final tree, not the historical 327-file ancestry. This reviewer wrote artifacts only under the dispatched scratchpad. Reviewer policy requires the lead/coder to retain the latest validated files under reviews/ in a trailing documentation commit before merge; that adds review custody documents outside the 63 expectation paths without changing corpus behavior. The user’s strict behavioral scope remains 63 expectations; if literal path-only scope forbids custody files, the lead must resolve that policy explicitly rather than silently dropping artifacts. QA 31 must squash first; the engine gitlink must subsequently name its actual squash SHA before engine 515 merges.

## Examined units

| # | Expectation file | Added own-criterion gaps | Independent semantic justification |
| --- | --- | --- | --- |
| 1 | cases/attachment/tag-at-module-scope-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Both moved test tags claim TC-001/002 only; both criterion identities lack claims even though aggregate targets are backed. |
| 2 | cases/attachment/tag-at-module-scope-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Both moved test tags claim TC-001/002 only; both criterion identities lack claims even though aggregate targets are backed. TypeScript text after the TC-id colon is prose; the declared comment form captures only the leading TC list. |
| 3 | cases/attachment/tag-at-module-scope/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The test-attached TC-002 still backs its aggregate; AC-2 has no own claim. The existing module-scope TC-001 and AC-1 gaps remain. |
| 4 | cases/attachment/tag-at-module-scope/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The test-attached TC-002 still backs its aggregate; AC-2 has no own claim. The existing module-scope TC-001 and AC-1 gaps remain. TypeScript text after the TC-id colon is prose; the declared comment form captures only the leading TC list. |
| 5 | cases/attachment/tag-inside-string-literal-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine comments claim TC-001/002, not AC-1; moving TC-002 out of a literal repairs that aggregate, not AC-1. |
| 6 | cases/attachment/tag-inside-string-literal-control/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine comments claim TC-001/002, not AC-1; moving TC-002 out of a literal repairs that aggregate, not AC-1. |
| 7 | cases/attachment/tag-inside-string-literal-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine comments claim TC-001/002, not AC-1; moving TC-002 out of a literal repairs that aggregate, not AC-1. |
| 8 | cases/attachment/tag-inside-string-literal/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine test claims TC-001 only, so AC-1 lacks its own claim; the TC-002 literal masking gap remains unchanged. |
| 9 | cases/attachment/tag-inside-string-literal/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine test claims TC-001 only, so AC-1 lacks its own claim; the TC-002 literal masking gap remains unchanged. |
| 10 | cases/attachment/tag-inside-string-literal/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The genuine test claims TC-001 only, so AC-1 lacks its own claim; the TC-002 literal masking gap remains unchanged. |
| 11 | cases/attachment/tag-on-describe-header-control/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Tags on both it symbols claim only TC identities; neither AC gains an own claim from moving the first tag off describe. TypeScript text after the TC-id colon is prose; the declared comment form captures only the leading TC list. |
| 12 | cases/attachment/tag-on-describe-header/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The standalone it claims TC-002 only; AC-2 lacks its own claim. Existing container-related TC-001/AC-1 gaps remain. TypeScript text after the TC-id colon is prose; the declared comment form captures only the leading TC list. |
| 13 | cases/attachment/tag-on-non-test-function-control/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The production Implements marker addresses AC-1 on the implementation channel; the unchanged test still claims TC-002 only, leaving AC-2 unverified. |
| 14 | cases/attachment/tag-on-non-test-function-control/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The production Implements marker addresses AC-1 on the implementation channel; the unchanged test still claims TC-002 only, leaving AC-2 unverified. |
| 15 | cases/attachment/tag-on-non-test-function-control/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The production Implements marker addresses AC-1 on the implementation channel; the unchanged test still claims TC-002 only, leaving AC-2 unverified. |
| 16 | cases/attachment/tag-on-non-test-function/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The admitted test claims TC-002 only; AC-2 lacks an own claim. The production-function tag behavior remains independently asserted. |
| 17 | cases/attachment/tag-on-non-test-function/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The admitted test claims TC-002 only; AC-2 lacks an own claim. The production-function tag behavior remains independently asserted. |
| 18 | cases/attachment/tag-on-non-test-function/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The admitted test claims TC-002 only; AC-2 lacks an own claim. The production-function tag behavior remains independently asserted. |
| 19 | cases/detection/test-name-id-in-fn-name-control/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The Rust tc_001 function-name form claims TC-001, not AC-1; aggregate backing does not supply the criterion identity. |
| 20 | cases/disposition/real-tests-zero-tags-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | The two test comments claim TC-001/002; each AC lacks its own claim despite the fully bound source census. |
| 21 | cases/disposition/real-tests-zero-tags-control/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | The two test comments claim TC-001/002; each AC lacks its own claim despite the fully bound source census. |
| 22 | cases/disposition/real-tests-zero-tags-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | The two test comments claim TC-001/002; each AC lacks its own claim despite the fully bound source census. |
| 23 | cases/join/tag-names-bare-fr-control/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so no AC-1 gap is added; the second still claims TC-002 only, leaving AC-2 unverified. |
| 24 | cases/join/tag-names-bare-fr-control/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so no AC-1 gap is added; the second still claims TC-002 only, leaving AC-2 unverified. |
| 25 | cases/join/tag-names-bare-fr-control/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so no AC-1 gap is added; the second still claims TC-002 only, leaving AC-2 unverified. |
| 26 | cases/join/tag-names-bare-fr/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only; AC-2 lacks its own claim. The first bare-FR defect and its diagnostics remain asserted. |
| 27 | cases/join/tag-names-bare-fr/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only; AC-2 lacks its own claim. The first bare-FR defect and its diagnostics remain asserted. |
| 28 | cases/join/tag-names-bare-fr/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only; AC-2 lacks its own claim. The first bare-FR defect and its diagnostics remain asserted. |
| 29 | cases/join/tag-names-undeclared-section-control/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so it stays backed; the second claims TC-002 only and AC-2 remains without its own claim. |
| 30 | cases/join/tag-names-undeclared-section-control/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so it stays backed; the second claims TC-002 only and AC-2 remains without its own claim. |
| 31 | cases/join/tag-names-undeclared-section-control/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The first test directly claims AC-1, so it stays backed; the second claims TC-002 only and AC-2 remains without its own claim. |
| 32 | cases/join/tag-names-undeclared-section/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only, leaving AC-2 unverified; the first INV identity and its undeclared-section behavior remain untouched. |
| 33 | cases/join/tag-names-undeclared-section/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only, leaving AC-2 unverified; the first INV identity and its undeclared-section behavior remain untouched. |
| 34 | cases/join/tag-names-undeclared-section/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims TC-002 only, leaving AC-2 unverified; the first INV identity and its undeclared-section behavior remain untouched. |
| 35 | cases/join/tag-names-unminted-tc-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Both repaired test comments claim TC-001/002 only; neither AC identity is claimed, so both own-criterion gaps are required. |
| 36 | cases/join/tag-names-unminted-tc-control/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Both repaired test comments claim TC-001/002 only; neither AC identity is claimed, so both own-criterion gaps are required. |
| 37 | cases/join/tag-names-unminted-tc-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001, FR-001-AC-2 → FR-001-AC-2,TC-002 | Both repaired test comments claim TC-001/002 only; neither AC identity is claimed, so both own-criterion gaps are required. |
| 38 | cases/join/tag-names-unminted-tc/python/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims minted TC-002 only, leaving AC-2 unverified; the first test has no claim and its existing gaps remain. |
| 39 | cases/join/tag-names-unminted-tc/rust/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims minted TC-002 only, leaving AC-2 unverified; the first test has no claim and its existing gaps remain. |
| 40 | cases/join/tag-names-unminted-tc/typescript/expect.yaml | FR-001-AC-2 → FR-001-AC-2,TC-002 | The second test claims minted TC-002 only, leaving AC-2 unverified; the first test has no claim and its existing gaps remain. |
| 41 | cases/minting/declared-heading-and-column-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The admitted test marker claims TC-001; its minted aggregate is backed while AC-1 lacks an own source claim. |
| 42 | cases/minting/declared-heading-and-column-control/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The admitted test marker claims TC-001; its minted aggregate is backed while AC-1 lacks an own source claim. |
| 43 | cases/minting/declared-heading-and-column-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The admitted test marker claims TC-001; its minted aggregate is backed while AC-1 lacks an own source claim. |
| 44 | cases/minting/id-column-mismatch/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The test marker claims TC-001 only; the independently declared AC-1 lacks an own claim. The null-row-id wrong-column gap is preserved. |
| 45 | cases/minting/id-column-mismatch/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The test marker claims TC-001 only; the independently declared AC-1 lacks an own claim. The null-row-id wrong-column gap is preserved. |
| 46 | cases/minting/id-column-mismatch/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The test marker claims TC-001 only; the independently declared AC-1 lacks an own claim. The null-row-id wrong-column gap is preserved. |
| 47 | cases/minting/no-testmatrix-document/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; AC-1 is independently declared and still has no own claim despite the absent TestMatrix. |
| 48 | cases/minting/no-testmatrix-document/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; AC-1 is independently declared and still has no own claim despite the absent TestMatrix. |
| 49 | cases/minting/no-testmatrix-document/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; AC-1 is independently declared and still has no own claim despite the absent TestMatrix. |
| 50 | cases/minting/rows-across-many-headings-control/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests still claim TC identities only; consolidating matrix headings repairs minting, not the AC-1 own claim. |
| 51 | cases/minting/rows-across-many-headings-control/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests still claim TC identities only; consolidating matrix headings repairs minting, not the AC-1 own claim. |
| 52 | cases/minting/rows-across-many-headings-control/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests still claim TC identities only; consolidating matrix headings repairs minting, not the AC-1 own claim. |
| 53 | cases/minting/rows-across-many-headings/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; spreading aggregate rows across headings does not provide an AC-1 own claim. |
| 54 | cases/minting/rows-across-many-headings/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; spreading aggregate rows across headings does not provide an AC-1 own claim. |
| 55 | cases/minting/rows-across-many-headings/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | All three tests claim TC identities only; spreading aggregate rows across headings does not provide an AC-1 own claim. |
| 56 | cases/minting/section-and-id-column/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading and column mismatch. |
| 57 | cases/minting/section-and-id-column/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading and column mismatch. |
| 58 | cases/minting/section-and-id-column/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading and column mismatch. |
| 59 | cases/minting/section-name-mismatch/python/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading mismatch. |
| 60 | cases/minting/section-name-mismatch/rust/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading mismatch. |
| 61 | cases/minting/section-name-mismatch/typescript/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | TC-001 is the sole test claim; AC-1 has no own claim regardless of the independently retained heading mismatch. |
| 62 | cases/parser/triple-quote-scope-desync/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The real pytest test claims TC-001; the phantom TC-999 is literal data. Neither is an AC-1 own claim; parser census assertions remain. |
| 63 | cases/parser/typescript-regex-brace/expect.yaml | FR-001-AC-1 → FR-001-AC-1,TC-001 | The admitted test invokes trace with TC-001 only; braces inside the regex do not create an AC-1 claim. Regex parsing assertions remain. |

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | low | No findings (placeholder) | - |

## Verdict

PASS: additive exact own-criterion gaps are consistent with unchanged counts, census, statuses, diagnostics and existing aggregate backing.
