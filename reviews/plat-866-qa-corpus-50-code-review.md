---
id: SR-20261103118147
title: "Code review of PLAT-866 structural implements reasons (qa-corpus PR 50)"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus; cases/attachment/implements-syntax-unattached*/**, cases/attachment/partial-implements-syntax-match*/**, corpus.yaml, modules/structural-implements/manifest.yaml, baselines/quire-rs.json, README.md (PR 50 diff vs origin/main only, head 405b101)"
review_set: subset
---

## Summary

Ticket: PLAT-866. PR head `405b101`. This is a read-only review of the qa-corpus diff, the companion of quire-rs PR 630 (head `0d94218`). The diff has no Rust, so no rust-review lane was needed.

The engine behaviour was measured, not assumed:

- A `quire` 0.38.4 binary was built from quire-cli `origin/main` (`b737daf`), with `quire-rs` patched to the PR 630 worktree. It reports engine 0.54.0.
- `make verify` ran with `QUIRE` set to that binary. The installed `spec-artifacts-process` 0.2.0 still declares `trace_tags.legacy`, which engine 0.54.0 rejects, so the run used a scratch `HOME` whose `.ix/filament/modules` held spec-artifacts-process at `origin/main` (`9fc6a8b`) and symlinks to the other installed modules. Result: 209/209 cases ran, 103 pairs were graded, and there was 1 mismatch. The mismatch is `mocked-confirmation-python`, a quoin `external_observations` line (13 expected, 16 observed) in a case this PR does not touch. All four new cases pass.
- `cargo run -- bounds --require-complete` gave 220 fixtures, 121 cells, 98 covered, 23 out of scope and GAP 0. The edited derived counts (`pairs=103`, `fixtures=220`, `failure_fixtures=102`, `controlled_failures=102`) agree with the tree.
- In a scratch quire-rs worktree at `0d94218`, with `corpus/` at `405b101`: `cargo test --test it corpus_` gave 32 passed and 0 failed. That includes `corpus_cases_hold`, `tc1028_a_failure_case_discriminates_from_its_control` and the recall ratchet. `UPDATE_CORPUS_RECALL=1` regenerated `baselines/quire-rs.json` byte-identically, so the hand edit equals the measurement.
- Direct runs gave `implements-syntax-unattached` at `src/lib.ts:1` with the value `implementing("FR-001")`, and `partial-implements-syntax-match` at `src/lib.py:1` with the value `@t.implements("FR-001")`. Both match the expected lines, paths and message fragments.

The module `modules/structural-implements/manifest.yaml` is not a vendored copy. Upstream spec-artifacts-process `origin/main` declares no `python_decorator` or `typescript_wrapper` form, and quire-rs PR 630 contains neither pattern string. It is a corpus-local fixture module in the same style as `guarded-implements` and `legacy-implements`. Its Python pattern is unanchored on purpose so that it matches a proper substring.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | Both controls assert only that the reason is absent, never that the relation binds. Each case comment claims that "the relation binds". Measured `coverage.implements` is matched 1 in each control and 0 in each failure, but neither control asserts `metrics`. When both control inputs were rewritten so nothing binds, `verify` still passed both pairs. The PLAT-1170 precedent `legacy-implements-form-control` asserts `metrics: coverage.implements {examined: 1, matched: 1}`. | cases/attachment/implements-syntax-unattached-control/typescript/expect.yaml:1, cases/attachment/partial-implements-syntax-match-control/python/expect.yaml:1, cases/attachment/implements-syntax-unattached-control/case.yaml:11, cases/attachment/partial-implements-syntax-match-control/case.yaml:11 |
| FND-002 | medium | Both failure cases declare "binds nothing and is reported", but `expect.yaml` asserts only the report. An engine that emitted the warning and also minted the relation would pass. The measured `coverage.implements` matched 0 (unattached examined 1, partial examined 2) is not asserted. | cases/attachment/implements-syntax-unattached/typescript/expect.yaml:1-7, cases/attachment/partial-implements-syntax-match/python/expect.yaml:1-7, cases/attachment/implements-syntax-unattached/case.yaml:6, cases/attachment/partial-implements-syntax-match/case.yaml:6 |
| FND-003 | medium | The partial-match pair is traced to the wrong criterion. It is tagged `TC-2201` and cites `FR-062-AC-19`, but TC-2201 says a renamed import `@t.implements("X")` "binds nothing and yields no finding". The `partial-implements-syntax-match` warning this case expects is FR-062-AC-25 / TC-2207. | cases/attachment/partial-implements-syntax-match/case.yaml:6, cases/attachment/partial-implements-syntax-match/case.yaml:9, cases/attachment/partial-implements-syntax-match-control/case.yaml:5, cases/attachment/partial-implements-syntax-match-control/case.yaml:8 |

## Verdict

Examined: all four new cases (metadata, inputs and expectations), the two `diagnostic_reasons` entries and derived-count edits in `corpus.yaml`, the README counts, the new module manifest, and the `baselines/quire-rs.json` edit.

What is right:
- The fixtures provoke the intended reasons at the expected lines.
- Each control changes exactly the one property under test: a `const` declarator for the unattached pair, and the unqualified decorator for the partial pair.
- The reasons are in alphabetical position.
- The derived counts and the baseline are exactly what the tree measures.

Not mergeable as is. FND-001 to FND-003 are medium and need a fix round: add `metrics: coverage.implements` to both pairs, and retag the partial pair to TC-2207 / FR-062-AC-25. The PR must land with quire-rs PR 630 or after it, because the installed engine predates both reasons.

The `mocked-confirmation-python` verify mismatch predates this PR. That case's input changed in #49 and its expected line did not. It still makes `make verify` red with quoin 0.29.1, which is outside this diff.

## Dispositions

Round 1, checked against fix head `6088a96`. Evidence for this round:
- `quire` 0.38.4 (engine 0.54.0) was built from quire-cli `b737daf`, with quire-rs patched to PR 630 head `7605461`. The scratch HOME modules hold spec-artifacts-process at `origin/main` (`b935498`).
- `make verify`: 211/211 cases, 104 pairs graded, 0 mismatches.
- With all three control inputs rewritten so nothing binds, `verify` reports `coverage.implements.matched expected 1, got 0` for each control, so the controls are no longer vacuous.
- `bounds --require-complete`: 222 fixtures, GAP 0.
- quire-rs at `7605461` with `corpus` at `6088a96`: `cargo test --test it corpus_` gives 32 passed, 0 failed, and `UPDATE_CORPUS_RECALL=1` leaves `baselines/quire-rs.json` unchanged.

The control's `examined: 2` against the failure's `examined: 1` is the engine's measured population, not an unexplained edit. It was already 2 at `405b101`. The control's `const control = implementing(...)(...)` declarator mints a Function symbol (FR-062-AC-23, FR-051-AC-51), and the failure's bare statement mints none.

The `ts-implementing-wrapper` pattern is no longer `\A`-anchored, which is deliberate and correct for this fixture module. FR-062's anchoring SHALL is the rule that shipped module patterns must follow. FR-062-AC-25's `partial-implements-syntax-match` exists to report a pattern that breaks it, and it can only be witnessed with an unanchored pattern, as the Python `@?implements\(` form already is. FR-004-AC-31..37 govern spec-artifacts-process's own manifest, not this corpus-local module. The unattached pair still yields no partial-match finding under the unanchored pattern, which was measured.

| FND | Outcome | Reason |
| --- | --- | --- |
| FND-001 | fixed | - |
| FND-002 | fixed | - |
| FND-003 | fixed | - |
