---
id: SR-013
title: "Code review of PLAT-263 validate-assurance make target (qa-corpus PR 43)"
type: SpecReview
analysis: code-review
scope: "agent-ix/qa-corpus; Makefile (PR 43 diff vs origin/main only)"
review_set: subset
---

## Summary

Ticket: PLAT-263. PR head `27992c2`. Read-only review of the Makefile part of the diff.

The PR adds a `validate-assurance` target and appends it to `ci`. The target runs `quire validate --scope "$(CORPUS_ROOT)" "assurance/*.md"`. `QUIRE` defaults to `command -v quire` and `CORPUS_ROOT` is the Makefile's own directory, so no path from one machine is hardcoded.

Measured failure behaviour, all on this machine:
- `make validate-assurance QUIRE=` prints `quire not found; set QUIRE=/path/to/quire` and exits 2.
- A document whose `type` has no installed archetype fails with `unknown type ... (no archetype registered for it)`, exit 3. So a missing `engineering-assurance` module fails. It does not skip.
- A glob that matches no files fails with `document glob matched no files`, exit 3.
- The PR's artifacts pass (exit 0). The `origin/main` artifacts fail 3 documents (exit 3). A deliberately broken section heading in a scratch copy fails (exit 3). The gate is not vacuous.

## Findings

| ID | Severity | Summary | Refs |
| --- | --- | --- | --- |
| FND-001 | medium | Makefile comment records a module version ("written against engineering-assurance 0.3.2"). That is version tracking, and it is wrong: quire resolves engineering-assurance 0.7.1. Delete the sentence. | Makefile:61-62 |

## Verdict

Examined: the help line, the `validate-assurance` recipe, the `ci` prerequisite list and the comment block. The target does what the ticket needs. It validates in `make ci`, fails loudly when quire, the module or the files are absent, and hardcodes no machine path. The one defect is the version sentence in the comment. Mergeable once it is deleted.
