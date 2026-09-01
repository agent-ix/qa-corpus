# Compatibility corpus

The accepted fixture set for the shared-assurance contract campaign. Consumed by
[`agent-ix/engineering-assurance` FR-011](https://github.com/agent-ix/engineering-assurance),
which pins this repository as a submodule and reads the corpus in place.

## Why it lives here and not there

It retains **real governance evidence** — PGM-01 records from
`agent-ix/quire-contract-ir`, real producer output, and one exact
Quire-to-Quoin receipt chain. `engineering-assurance` is a public repository
whose publication boundary permits fictional fixtures only and lists
`operational-evidence` as prohibited. This repository is private and exists to
hold real artifacts read in place, so the corpus lives here and the gate reads
it from here.

## What it contains

| Path | Contents |
| --- | --- |
| `corpus.json` | The index: every case, its digest, origin, derivation, and expected outcome |
| `records/` | Retained PGM-01 record bytes, real and derived |
| `producers/` | Retained real producer output |
| `chain/` | The Quire-to-Quoin receipt chain, artifact by artifact |
| `sources/` | Inputs a case is built from that are not themselves cases |

## What is real and what is not

Three records are real, byte-for-byte, read through `git show origin/main:<path>`
at a recorded revision and matched against the digests `quire-contract-ir`
recorded for them.

The rest are **derived**, because the history does not contain them. All ten
retained PGM-01 records in that repository are v1 and carry only `pass`,
`skipped`, and `inconclusive` — there is no failed, unavailable, not-computed,
stale, or tampered record anywhere in it. Each derived case is one named edit to
real bytes, and records that edit and the reason for it. A reader can tell a
found record from a constructed one without reading a diff.

PGM-01 v1 has no `not_computed` status at all. The mapping refuses one rather
than inventing a translation, and the corpus records that refusal as the
expected outcome.

## What is referenced rather than retained

Three artifacts are pinned by digest and not copied in, each for a stated
reason: the external-engine result embeds third-party advisory prose, the
agent-evaluation result records an absolute transcript path, and the Quire
export records the absolute module-manifest path of the machine that produced
it. The retained attestation binds the export's exact bytes, so the chain stays
verifiable for a holder of them.

## Rebuilding

```bash
ASSURANCE_SOURCE_ROOT=/path/to/checkouts python3 scripts/build_compatibility_corpus.py --check
```

`--check` verifies that the committed corpus still reproduces from its recorded
sources and writes nothing. Without it, the corpus is rewritten — which is how a
maintainer refreshes it after a source repository advances.

## Not a bounds case

This directory is outside `cases/`, so `bounds.py` does not govern it. It is not
a detection or minting case with a language inventory; it is retained evidence
with an expected mapping outcome per record. Its gate is FR-011's test in
`engineering-assurance`, not `make bounds`.
