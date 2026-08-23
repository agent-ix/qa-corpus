# qa-corpus

The controlled corpus for the `quire` / `quoin` toolchain. **Static files, read in
place, language-neutral.** Contract: [`agent-ix/quire-rs` FR-065](https://github.com/agent-ix/quire-rs/blob/main/spec/functional/FR-065-controlled-corpus-contract.md).

## Why this repository exists

Both previous corpora were embedded in code and neither could be read without
running it — mini-repositories as strings in a JSON blob on one side, template
literals materialised to a tmpdir on the other.

Worse, the JavaScript generator declared **its own manifest**: `section: Test Cases`
where the ecosystem declares `Test Case Summary`. A corpus bound to a manifest whose
heading always matches **cannot exhibit** the defect accounting for **3,514 unminted
TC ids across 88 repositories**. Tier 1 never caught the dominant failure mode
because tier 1 was built where that mode cannot occur.

## Reproducing a case

That is the whole reproduction — no harness, no generator, byte-identical to what CI
runs:

```bash
cd cases/attachment/marker-form-mismatch/input
quire coverage --scope . --module ./module --json
```

`--module` is not decoration. Without it no traceability model loads, the run reports
`0/0 rows backed`, and the case cannot exhibit the declaration defect it exists for.

Each case's own invocation is recorded in its `case.yaml` under `reproduce`.

## Layout

```
corpus.yaml          schema version, vocabularies, case index, the bounds matrix
modules/
  ecosystem/         THE REAL declaration, vendored with its source SHA (VENDORED.md)
  variants/<id>/     relaxation variants — each names the ticket it sizes
cases/<mode>/<case>/
  case.yaml          id, issue_ref, mode, language, module, findable, kind, reproduce
  input/             REAL STATIC FILES — full topology, cd-able, runnable by hand
  expect.yaml        what the run must show. Data, not assertions in code.
labels/              hand-labelled ground truth for finding-quality scoring
config/              the metric dictionary
baselines/           per-runner baselines, versioned with the corpus
```

## The bounds matrix is the point

A case list answers *what did we try*. The matrix answers **what did we never try**,
and only the second is a statement about the tool. Every declared cell is `covered`,
`out-of-scope` with a written reason, or `GAP`.

**A scenario with no case is undefined behaviour, not assumed-working.** `v0.44.0`
shipped two `high` defects straight through the empty Python and TypeScript columns.

`bounds.gap_count` is a **count, never a ratio**. A ratio falls as easy cases are
added, so a corpus could improve its number while the hard missing case stayed
missing. Converting a `GAP` to `out-of-scope` moves the count — declaring something
out of scope is a visible act.

### Today: `gap_count: 36`, and nothing is `covered`

The ten cases here are ports of the existing `quire-rs` fixtures, and **all ten bind
the `bench-legacy` variant** — the synthetic manifest described above. They therefore
cover **no ecosystem mode**, and the matrix says so rather than crediting them.
Rebinding them to the real declaration changes what they assert, which is migration
work with its own before/after: `agent-ix/quire-rs#285`.

Starting at zero covered is the honest reading. A corpus that credited itself on day
one for cases bound to a manifest that cannot fail is the exact defect this repository
was created to end.

## Detection is graded

| Level | Question |
|---|---|
| L1 detected | Did anything fire? |
| L2 localised | Did it name the right `path:line`? |
| L3 actionable | Did the message name the thing to change? |

A failing case reports **which level was lost** — "the case failed" and "the message
stopped naming the row" are different repairs.

These levels are **not** interchangeable with `quoin`'s `actionability_rate`, which
spans L2 and L3 together. Both stand; a cross-runner comparison treating them as one
quantity does not.

## Every failure case ships its control

A detector that fires on everything scores perfect recall. `quire-rs#250` shipped a
check producing **549 suspicions from 551 candidates**, and recall alone called it
excellent. A control is healthy input that must stay silent; a failure case names its
control with `control_for`.

## Licence

AGPL-3.0-or-later. Per the agent-ix licensing policy — no carve-outs.
