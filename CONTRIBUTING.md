# Contributing cases

Every dogfood or census finding must become a controlled corpus case before its
fix lands. File the issue first, bank the failing behavior, and keep
`issue_ref` on every failure, control, and regression record. A pending case is
the supported way to preserve the red state without making the tracking branch
permanently red; remove `pending` only when the fix makes its forward
expectation hold.

## Required loop

1. Record the real locus, tool/module revisions, reproduction, and measured
   blast radius on the issue.
2. Add the failure case before changing the detector. Declare every supported
   language in the inventory. Each applicable cell must have a case; use
   `out_of_scope` only when the mode cannot occur in that language, and give the
   reason. "Not implemented" and "expensive" are GAPs, not exclusions.
3. Add a language-matched healthy control. Its payload must stay silent, and the
   failure expectation must differ from it through a witness channel declared
   for that mode.
4. Run `make ci` with the pre-fix engine and retain the expected-pending result
   on the issue. Then fix the tool, promote the forward expectation, rerun the
   gates, and rerun the census or dogfood measurement that found the mode.
5. Report the estimate and realized delta with exact revisions and populations.
   Do not claim a causal delta from unrelated changes in the same sweep.

`make bounds` is the CI policy check. It rejects a GAP, a missing or empty
`issue_ref`, an unexplained exclusion, or a failure without a language-matched
control. `python3 bounds.py` remains available while authoring to display an
incomplete matrix without treating it as a passing gate.

## Banking a real tree (Tier 2)

Use a Tier-2 tree only when scale, topology, or interaction between files is
necessary to reproduce the finding. Prefer a minimal Tier-1 case when it
preserves the actual failure mechanism.

1. Create a purpose-specific snapshot repository. Remove secrets, credentials,
   personal data, generated artifacts, and irrelevant history, but preserve
   every path and byte required by the reproduction. Record the source
   repository and source commit in that snapshot.
2. Reproduce the pre-fix failure from the snapshot commit. Record its command,
   engine/module revisions, expected finding and healthy control on the issue.
3. Add the snapshot under `tier2/<case>` as a Git submodule and check out an
   exact commit, never a floating branch. Commit the `.gitmodules` entry and
   gitlink together with `tier2/<case>.md`, which records the issue, source and
   snapshot SHAs, sanitization review, reproduction, control, and oracle.
4. Wire one explicit Tier-2 target into CI, initialize submodules recursively,
   and fail if the checked-out gitlink differs from the recorded snapshot SHA.

Moving a Tier-2 pin is the reviewable event. It requires a ticket, a before run
at the old pin, an after run at the proposed pin, re-adjudication of every
changed label and expectation, and a published metric delta. Commit the new
gitlink, evidence update, and ratchet change together. A routine dependency
refresh is not authority to move a corpus pin.

## First completed end-to-end loop: quire-rs#363

The 2026-08-26 census found three Quoin `SUITE-*` registry rows presented as
repository authoring backlog. The `reference-only-target` case and control were
banked at qa-corpus `fb39e05`; the old engine failed the pending contract, and
the fixed engine made it pass before the marker was promoted at `0a29a2b`.

The direct realized delta is three false suite obligations removed. The
provisional whole-corpus run had P3 26,727, P4 20,098, backed 5,393 and
`authoring-absent` 12,434. The repeatable 241/241 report at Quire `9d28eb7`
contains no `SUITE-*` or `INSP-*` obligation, has P3 26,726, P4 20,097, backed
5,395 and `authoring-absent` 12,431, and passes its 26,726-row invariant. The
other net changes came from concurrent real source/spec additions and are not
attributed to #363. The final JSON and Markdown hashes and full gate evidence
are recorded on `agent-ix/quire-rs#277` and `#363`.
