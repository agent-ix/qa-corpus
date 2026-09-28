---
id: SR-002
title: "Code review — range-in-trace-tag corpus cases (qa-corpus#25)"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus@2ccc2e54fe702dadbe61827d120396c60d365ea9; diff vs 7442f27 (contract-agent-core/reference-status-column-409): README.md, baselines/quire-rs.json, corpus.yaml, scripts/parity_selftest.py, cases/attachment/range-in-trace-tag/**, cases/attachment/range-in-trace-tag-control/**"
review_set: subset
---

## Summary

Ticket: PLAT-1077 (companion to quire-rs#495, which pins this commit). PR:
qa-corpus#25 at `2ccc2e5`, 4 commits, 36 files, +330/−26, reviewed against its
base `7442f27`. The base is the unmerged qa-corpus#14; that drift is PLAT-1089
and is not assessed here.

What the PR does:

- registers `range-in-trace-tag` in the `diagnostic_reasons` vocabulary
- banks a three-language failure case and a matched control
- re-derives the `<derived:...>` counts (pairs 85→88, fixtures 189→195, failure fixtures 84→87)
- re-baselines detection recall: +1 attachment population per language

The cases are well formed. The control differs from the failure case in the
right witness: `backed` 2 vs 0 and the reason being absent. quire-rs
`corpus_cases` runs them green (19/19) on the pinned engine.

Local gates at `2ccc2e5`:

| Gate | Result |
| --- | --- |
| `make bounds` | exit 0 |
| `make schema-selftest` | exit 0, 22/22 |
| `make duplicate-census` | **exit 1** |

The PR has no GitHub checks: none are reported on the branch, because its
base is not `main`.

## Verdict

**FAIL, not mergeable as-is.** The corpus's own `make ci` fails at the
`duplicate-census` stage because of files this PR adds (FND-001). The fix is
mechanical.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | high | `make duplicate-census`, a `make ci` prerequisite, fails with "unexplained fixture-copy drift". It reports three new copy groups, all made of this PR's files: the six identical `input/spec/FR-001.md`, the six `input/spec/tests.md` (plus `detection/catch-all-properties`), and the three control `expect.yaml`. The census was never updated. Failure scenario: `make ci` is red for the next contributor after merge, and the gate's purpose (every duplicate is explained) lapses. Fix: review the groups, run `python3 scripts/duplicate_census.py --update`, and commit the census with the cases. | Makefile:72, cases/attachment/range-in-trace-tag/rust/input/spec/FR-001.md:1, cases/attachment/range-in-trace-tag-control/rust/expect.yaml:1 |
| FND-002 | low | The cases bank only the same-prefix **marker** form. Under the old engine a marker range already gave `backed: 0`, so only the diagnostic discriminates old from new. The behaviour change that moves counts is the legacy `// Trace: A..B` form, which used to bind `A`. That form, and the differing-prefix and short-suffix shapes, are not in the corpus. They are pinned only in quire-rs TC-1937. A second engine (the corpus's purpose) would not be held to them. | cases/attachment/range-in-trace-tag/rust/input/src/lib.rs:5, cases/attachment/range-in-trace-tag/rust/expect.yaml:1 |

## Dispositions

Reviewed at `agent-ix/qa-corpus@cbe1c5a579fadee8ac6b1a1599b2933b7b23fab8`.

| FND | outcome | sha/reason |
| --- | --- | --- |
| FND-001 | fixed 46379f3 | `config/duplicate-census.json` records the new copy groups, and `make duplicate-census` now exits 0. Also exit 0 at cbe1c5a: `schema-selftest` (22/22), `external-channel`, `bounds`, `measurement-selftest` and `verify-reporting`. |
| FND-002 | fixed 46379f3 | Banks `range-in-legacy-trace-tag` (whose control, a legacy list, has `backed: 2`; the failure case has `backed: 0`, where the old engine gave 1), plus `range-differing-prefix-in-trace-tag` and `range-short-suffix-in-trace-tag`, in all three languages. |
| FND-003 | fixed 876a170 | `tag-on-non-binding-symbol` was added to `absent_diagnostic_reasons` for the legacy, marker, short-suffix and differing-prefix range cases in all 3 languages. Against quire-rs 165a1d3 every case holds (see the SR-120 probe), and removing the engine's R1 filter would now turn the corpus red too. |

`make verify` and `parity-selftest` need a quire CLI that contains this engine change (PLAT-1078), so they were not run. The new cases are instead exercised against this branch's engine through quire-rs at 1249085 (corpus pinned to cbe1c5a): `corpus_cases` passed 19/19, including `corpus_cases_hold` over every case and `tc1028_a_failure_case_discriminates_from_its_control`, and `corpus_recall` passed 2/2.

## New findings (disposition pass 2)

Reviewed at `agent-ix/qa-corpus@cf10e6bb84bef072069dd3428b36dbf245f7c86c`. The only change since cbe1c5a is `reports/26-09-27-plat-1077-qa-corpus-code-review.md` (+11 lines).

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-003 | low | `range-in-legacy-trace-tag/*/expect.yaml` lists only `untracked-id-near-miss` under `absent_diagnostic_reasons`. Against the engine at quire-rs 74460ae, the case also emits a false `tag-on-non-binding-symbol` (quire-rs SR-120 FND-018), and the corpus stays green. Add `tag-on-non-binding-symbol` to `absent_diagnostic_reasons` in all three languages, and do the same for the marker range cases, so a second engine is held to it too. | cases/attachment/range-in-legacy-trace-tag/rust/expect.yaml:10 |

### Round 2 dispositions

No finding was open going into this round (FND-001 and FND-002 were fixed in round 1), so there are no disposition rows. `corpus_cases` passes 19/19 and `corpus_recall` passes 2/2 against quire-rs 74460ae with the corpus pinned at cf10e6b.

Round 3 at `agent-ix/qa-corpus@876a170a97bf27ce56b50a183c748d23bfb6828a`: the census re-group only re-hashes the same three expect.yaml pairs (rust, python, typescript) after the content change, so no pair was added or dropped. `make` schema-selftest, duplicate-census, external-channel, bounds, measurement-selftest and verify-reporting all exit 0. No open findings.
