---
id: SR-16441
title: "Gap analysis of qa-corpus PR 49 cases against quire-rs FR-051-AC-22, AC-24, AC-49 and AC-50"
type: SpecReview
analysis: gap-analysis
scope: "agent-ix/qa-corpus; cases/attachment/tag-at-module-scope*/**, cases/attachment/tag-on-non-test-function*/**, cases/attachment/tag-on-describe-header*/**, cases/attachment/tag-inside-string-literal*/**, cases/detection/stale-name-correct-trace/**, cases/detection/untracked-id-near-miss*/** (PR 49 head a37b2d6), against quire-rs main spec/functional/FR-051-source-symbol-extraction.md"
review_set: subset
---

## Summary

Ticket: PLAT-847. PR head `a37b2d6`. Plan completion: not assessed.

qa-corpus has no spec tree of its own, so `quoin matrix` does not apply. This check maps the four criteria named in the brief to the corpus cases by hand. The criterion text was read from quire-rs `main` (`e1f5315`), where CR-215 has already landed.

Every emitted reason still has a failing case and a healthy control: `bounds --require-complete` reports GAP 0, and the corpus reader's reason-coverage check passes. `trace-id-outside-marker` is asserted present by 6 failing fixtures:
- `tag-at-module-scope`: python, typescript
- `tag-on-non-test-function`: python, rust, typescript
- `tag-on-describe-header`: typescript

It is asserted absent by 10 fixtures:
- the controls of `tag-at-module-scope` and `tag-on-non-test-function`
- both sides of `tag-inside-string-literal`

`tag-on-non-test-function-control` covers the AC-49 rule that an id an `implements` form reads goes only to FR-050-AC-62: its `Implements: FR-001-AC-1` must stay silent. The module declares no `syntax: rust_attribute` implements form, so AC-22 says a production function's finding names the kind alone. Dropping the old `Implements:` fragment assertion is therefore correct.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | No case covers AC-49's main path. No failing case puts a comment id on an evidence symbol (a test) and asserts the replacement text: `#[trace("TC-001")]`, `@pytest.mark.trace("TC-001")` or `trace("TC-001")`. No case covers AC-50's "fires even when backed" rule either. Every failing case uses a non-binding kind, so the canonical-text advice, the main deliverable of PLAT-847, has no corpus witness. | cases/attachment/tag-at-module-scope/python/expect.yaml:54-60 |
| FND-002 | medium | AC-22 says the finding names the symbol's kind, but `tag-at-module-scope` (python, typescript) and `tag-on-describe-header` dropped their `container` kind fragment. No advisory case asserts `diagnostic_lines`, although AC-49 requires the line, the harness supports it, and each expect header says the finding "names the file, line, symbol and kind". | cases/attachment/tag-at-module-scope/python/expect.yaml:56-58, cases/attachment/tag-on-describe-header/expect.yaml:52-55 |
| FND-003 | medium | AC-22 says a non-binding kind gets no `#[trace(...)]` replacement text. No case can witness that: the harness has only `diagnostic_message_contains`, with no excluded-fragment key. An engine that tells a production function or module to grow a `trace` marker, which binds nothing, passes the corpus. | cases/attachment/tag-on-non-test-function/rust/expect.yaml:55-60, src/verify.rs:712-729 |
| FND-004 | medium | `tag-on-describe-header-control` does not assert `trace-id-outside-marker` absent. Its `absent_diagnostic_reasons` lists only the three census reasons. It is the only advisory control without the absence check. | cases/attachment/tag-on-describe-header-control/expect.yaml |
| FND-005 | medium | The `tag-inside-string-literal` pair does not test the AC-24 mask. The string holds `Trace: TC-002`, which has no comment shape, so a line-oriented comment scanner with no mask stays silent too. AC-50 already excludes body tokens. Since CR-215, `Trace:` binds in no engine, so the binding half of the pair is vacuous. Comment-shaped data such as `"# TC-002"` or `"// TC-002"` would make it discriminate. | cases/attachment/tag-inside-string-literal/python/input/src/thing.py:13-15, cases/attachment/tag-inside-string-literal/rust/input/src/lib.rs:12 |
| FND-006 | medium | `stale-name-correct-trace` was rewritten into a generic "marker id with no row is untracked" case, and its name now misdescribes it. With the `test-name-id-*` cases deleted, nothing witnesses CR-215's rule that a test name binds nothing. Keeping the stale name with marker `TC-001` and expecting `untracked_symbols: []` would witness that rule. The rewrite also dropped `#[cfg(test)]` without saying why. | cases/detection/stale-name-correct-trace/rust/input/src/lib.rs:3-8, cases/detection/stale-name-correct-trace/typescript/input/src/coverage.test.ts:1-2 |

## Verdict

Examined: FR-051-AC-22, AC-24, AC-49 and AC-50 against the rewritten failing cases and controls. Also examined: the `untracked-id-near-miss` pair (FR-050 #307 near-miss, present and absent) and the deleted cases.

AC-49 (non-binding kinds), the AC-49 implements exclusion and AC-50's all-markers-silent rule are witnessed. AC-49's evidence-kind path (FND-001), AC-22's kind and no-marker-text clauses (FND-002, FND-003) and AC-24's mask (FND-005) are not. The deleted cases test only removed machinery. The renamed near-miss case tests a real, emitted behaviour.

Not mergeable until these findings are fixed or dispositioned.
