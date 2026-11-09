---
id: SR-014
title: "Spec review of PLAT-263 assurance artifact realignment (qa-corpus PR 43)"
type: SpecReview
analysis: base
scope: "agent-ix/qa-corpus; assurance/AP-201-controlled-corpus.md, assurance/MP-201-gap-count.md, assurance/MP-202-detection-recall.md (PR 43 diff vs origin/main only)"
review_set: subset
---

## Summary

Ticket: PLAT-263. PR head `27992c2`. Read-only review of the three assurance artifacts.

Validation, measured on this machine with quire 0.36.2 (engine 0.50.2) and quoin 0.29.1:
- `quire validate --scope . "assurance/*.md"` on the PR head exits 0. This is the form `make validate-assurance` runs. The module set quire resolves includes `engineering-assurance` at commit d1de13a, whose `manifest.yaml` says version 0.7.1 (v0.7.1 plus 5 commits).
- The same command on `origin/main`'s artifacts exits 3, with 3 documents failing. So the PR fixes a real failure.
- The ticket's form, `IX_FILAMENT_MODULES_PATH=~/dev/engineering-assurance quire validate --scope . "assurance/**/*.md"`, exits 3 here, with `AP-201: Additional properties are not allowed ('schema_version' was unexpected)`. This is an environment issue, not a defect in the PR. That checkout is a stale branch at version 0.3.1. It adds a second `engineering-assurance` (`DuplicateModuleName ... first-wins`), and the stale copy wins.

The PR's own claims of "engineering-assurance 0.3.2" and "quire 0.38.3" do not match what resolves here. The artifacts validate against the installed 0.7.1.

MP-201 and MP-202 change only section headings: Decision Objective becomes Decision Use, Population and Scope becomes Population, Environment and Sampling becomes Collection Procedure, Interpretation and Limitations becomes Interpretation. Their bodies are unchanged. AP-201 moves the old `impact`, `dimensions`, `rationale` and `uncertainty` text into the Impact Scenarios prose. Consequence, reversibility, scope of effect, detectability, recovery and the uncertainty statement all survive, with their meaning intact. `tier: material` becomes `severity: material`. `lifecycle` is dropped. The schema has no such field, and the applicability prose still covers it.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | Each artifact gains the line "Written against the `engineering-assurance` module, version 0.3.2." That is a version record, which is ceremony under the no-version-tracking rule, and it is false: the validator resolves 0.7.1. Delete all three lines. | assurance/AP-201-controlled-corpus.md:22, assurance/MP-201-gap-count.md:15, assurance/MP-202-detection-recall.md:15 |
| FND-002 | low | `schema_version: 0.2` is an optional version assertion. The schema makes it optional, and AP-201 validates without it. It guards nothing, so delete it. | assurance/AP-201-controlled-corpus.md:7 |
| FND-003 | medium | The review set changed meaning. `[evidence, integrity, scope-boundary]` became `[spec-review, gap-analysis]`. The three original analyses are all spec-review sub-analyses, so `spec-review` covers them, but the specific sub-analyses are no longer named anywhere. `gap-analysis` is a new requirement that was never in the profile. The PR body also says the enum is `[spec-review, gap-analysis]`, but the schema enum also includes `code-review`. | assurance/AP-201-controlled-corpus.md:15-17 |

## Verdict

Examined: the AP-201 frontmatter and every body section, and the MP-201 and MP-202 frontmatter and every section. All three validate against the resolved module, and the realignment preserves meaning, except for the review set in FND-003. FND-001 and FND-002 are version records to delete. For FND-003, use `operations: [spec-review]` and name the evidence, integrity and scope-boundary analyses in the Evidence Policy prose. Keep `gap-analysis` only if the owner deliberately wants it added. Mergeable once FND-001 to FND-003 are fixed.
