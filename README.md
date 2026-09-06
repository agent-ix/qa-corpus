# qa-corpus

The controlled corpus for the `quire` / `quoin` toolchain. **Static files, read in
place, language-neutral.** Contract: [`agent-ix/quire-rs` FR-065](https://github.com/agent-ix/quire-rs/blob/main/spec/functional/FR-065-controlled-corpus-contract.md).

Case-before-fix, language, control, and Tier-2 pin policy lives in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Why this repository exists

Both previous corpora were embedded in code and neither could be read without
running it — mini-repositories as strings in a JSON blob on one side, template
literals materialised to a tmpdir on the other.

Worse, the JavaScript generator declared **its own manifest**: `section: Test Cases`
where the ecosystem declares `Test Case Summary`. A corpus bound to a manifest whose
heading always matches **cannot exhibit** the defect whose candidate census is **3,514 unminted
TC ids across 88 repositories**. Tier 1 never caught the dominant failure mode
because tier 1 was built where that mode cannot occur.

## Reproducing a case

That is the whole reproduction — no harness, no generator, byte-identical to what CI
runs:

```bash
make verify                     # every case, by its own recorded invocation
make verify-reporting           # Quoin report over static record pairs
make bounds                     # derive the matrix; reject every applicable GAP
make measurement-collection OUTPUT=/tmp/qa-corpus.json
                                # derive the two plan-owned collection families
make duplicate-census           # reject unexplained copied-fixture divergence/groups
make external-channel           # validate exact non-Quire producer/invocations
```

Or one case by hand, **from the corpus root** — this is exactly what CI runs:

```bash
IX_FILAMENT_MODULES_PATH=modules/ecosystem \
  quire coverage --scope cases/attachment/marker-form-mismatch/input --json
```

Naming the module is not decoration. Without it no traceability model loads, the run
reports `0/0 rows backed`, and the case cannot exhibit the declaration defect it exists
for. The ecosystem declaration is a module **path** — `spec-artifacts-process` *and*
`spec-artifacts-iso` — so it is selected with `IX_FILAMENT_MODULES_PATH`;
`--module` takes one directory and is what a variant-bound case uses.

It runs from the root because the CLI **refuses a `..` segment** in `--module` under
path safety, so a `cd input && … --module ../../../../modules/…` form is rejected
(agent-ix/quire-rs#287).

Each case's own invocation is recorded in its `case.yaml` under `reproduce`, and
`make verify` runs exactly that string — so a documented command that does not work
fails the corpus rather than misleading a reader.

Reporting cases are equally direct. For example:

```bash
quoin report \
  --repo cases/reporting/definition-version-changed/input \
  --since before --format json
```

They are a separate measured population: Quoin compares two checked-in
MeasurementCollections and `verify-reporting` grades the exact JSON twice. The
second render must be byte-identical. They share the inventory and GAP ratchet,
but never enter Quire detection recall or Quoin Tier-1 finding scores.

## Layout

```
corpus.yaml          schema version, vocabularies, `case_schema`, and the INVENTORY
                     (intent only — the case index and the matrix are DERIVED)
bounds.py            derives the matrix and gap_count from the filesystem
verify.py            runs every case by its own `reproduce`, diffs expect.yaml, and
                     grades each failure case against its CONTROL's payload (AC-42)
scripts/
  verify_reporting.py grades reporter output over static MeasurementCollections
  schema_selftest.py mutates a copy of the corpus and requires bounds.py to reject it
  parity_selftest.py blinds a fixture and requires verify.py's differential to reject it
modules/
  ecosystem/         THE REAL declaration, vendored with its source SHA (VENDORED.md)
  variants/<id>/     relaxation variants — each names the ticket it sizes
cases/<mode>/<case>/                       ONE language
  case.yaml          the fields `corpus.yaml`'s `case_schema` declares. Read it
                     there rather than here: a list of required fields written in
                     prose is a second declaration free to rot, and this one had
                     (#336). `make new-case` scaffolds a complete skeleton.
  input/ expect.yaml

cases/<mode>/<case>/                       a LANGUAGE SET
  case.yaml          everything SHARED — the identity fields
  <language>/
    case.yaml        only what VARIES: reproduce, per-language overrides
    input/ expect.yaml

cases/reporting/<case>/                    a REPORTING case (`language: data`)
  case.yaml          a hand-runnable `quoin report` invocation
  input/spec/evidence/measurements/*.json  two static collections (one for no-prior)
  expect.yaml        exact machine report and byte-identity requirement

`language` comes from the DIRECTORY NAME, never a declared field. A variant's id
is `<shared id>-<language>` in every reader, and a variant may not override
`case`, `mode`, `module`, `kind` or `pending` — those declare WHICH case it is,
and varying them re-points the cell it credits (FR-065 CR-109).
  input/             REAL STATIC FILES — full topology, cd-able, runnable by hand
  expect.yaml        what the run must show. Data, not assertions in code.
labels/              hand-labelled ground truth for finding-quality scoring
config/              the metric dictionary
baselines/           per-runner baselines, versioned with the corpus
```

`config/duplicate-census.json` classifies every byte-identical fixture group.
Cases stay self-contained, so intentional support files are copied rather than
symlinked; their invariant is that copies move together unless the seeded defect
requires divergence. When a reviewed fixture change intentionally alters group
membership, run `python3 scripts/duplicate_census.py --update`, inspect the exact
paths/digests, and commit the fixture and census in one change. A new group, a
disappeared group, or unexplained membership change fails CI.

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

The corpus owns the `bounds.gap_count` and partitioned `detection.recall`
definitions and stores their collections here. `scripts/export_measurements.py`
accepts no values: it derives bounds from the filesystem and recall from the
Quire and Quoin runner-produced baselines, retaining the runner boundary in
every observation. Quire and Quoin own their engine- and finding-quality plans;
engineering-assurance and spec-artifacts-process intentionally own no producer
or measurement store in this QA program.

### Today: run `make bounds`

Run `make bounds` — these numbers are **derived, never stored**, so they cannot go
stale. Adding a fixture flips its own cell and moves the count with no edit to any
central file.

`agent-ix/quire-rs#285` migrated the ported detection cases off `bench-legacy` —
the synthetic manifest whose heading always matches — and deleted it. Detection
fixtures bind either the vendored ecosystem declaration or an explicitly attributed
declaration-under-test variant; reporting fixtures exercise Quoin and do not load a
traceability module despite retaining the common metadata field.

A cell covered by a **pending** fixture is reported separately: a case exists and
the engine fails it, and `covered` read as `working` is the conflation this
corpus exists to end.

A corpus that credited itself on day one for cases bound to a manifest that cannot
fail is the exact defect this repository was created to end, which is why the count
started near zero and why it moves one migration at a time.

### A fixture may be red before its fix

`pending: <ticket>` means a case asserts behaviour the engine does not have yet. It
is **expected to fail**, is counted and printed, and the suite still goes green —
which is what makes *case red before fix* workable rather than a choice between a
red build and writing the fixture after the fix.

A pending case that **passes** fails the run, naming the ticket that appears to have
landed, so stale markers cannot accumulate.

A pending case carries **two** blocks, and both are graded:

| file | contract | must |
| --- | --- | --- |
| `expect.yaml` | what holds **today** | HOLD, for every case, pending or not |
| `expect-pending.yaml` | what the ticket will make hold | NOT hold yet |

Declaring one without the other is rejected.

> **This retired an earlier rule** — *"a pending case asserts only what is pending;
> anything already true belongs in the control"* — which this README carried until
> the outside review of 2026-08-24 found it still here. That rule was a consequence
> of `pending:` excusing a case's whole expectation block, and it left every live
> fact unasserted: both minting fixtures could have regressed to minting nothing, in
> three languages, and stayed green. A control cannot hold a failure case's live
> facts, because its input is healthy. See FR-065's Behavior section.

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

**Naming one is not enough, and that is the point.** Your `expect.yaml` is also graded
against your control's payload, and it must produce **at least one mismatch** there
(FR-065-AC-42). A block that holds against healthy input is not about your defect,
whatever its shape — an empty block cannot mismatch, and neither can a row count that
is true of both trees. So assert the field that *separates the pair*, not the field
that happens to be handy. Both readers do this since `agent-ix/quire-rs#337`; before
it, only `cargo test` did, and `verify.py` reported `mismatches: 0` on a corpus the
Rust harness rejected.

**And through your mode's own channel, not any channel** (FR-065-AC-46). The block is
graded a *second* time with every key outside `witness_channels[<your mode>]` dropped,
and the restriction must still mismatch. So "assert the field that separates the pair"
is not the whole rule: the field also has to be one your mode declares. `total` is a
witness for `minting` and for **nothing else** — a minted-row count *is* the minting
channel, and everywhere else it is an incidental global scalar. Measured over the whole
controlled population, 15 of the <derived:pairs=79> (case, control) pairs differ in `total`
while being about something else entirely, which is what this closes. The pair count is
gated against the tree; the 15 is a measurement at engine `5a68ceb` and is not.

Read `witness_channels` in `corpus.yaml` for your mode before you write `expect.yaml`.
A block that names none of them is rejected by name; so is one that separates the pair
only outside them. A channel name the readers cannot restrict on is rejected at load
rather than dropped (FR-065-AC-47), so the declared set and the graded set cannot drift.

Three more consequences worth knowing before you write a fixture:

* `validate_*` keys are re-run over the **control's** tree in that grading, because
  `quire validate` reads a spec tree and cannot be recomputed from a payload. They are
  a witness in **every** mode: `quire validate` is a second oracle, not a coverage
  channel. The rule's reach over this corpus is 1 pair of <derived:pairs=79>: it read
  "0 of 35" until `wrong-type-cell` gained a control, and nothing was holding that
  sentence to the tree.
* If your case is `pending:` on a **behaviour-change** ticket — one that adds no
  diagnostic — its `expect-pending.yaml` is held to the opposite rule: it must
  **hold** against the control, which is the tree the engine should produce once the
  fix lands. A forward block that fails against it describes no reachable state.

`make parity-selftest` blinds a real fixture and requires the differential to reject
it, so the rule is a behaviour rather than a claim.

## Licence

AGPL-3.0-or-later. Per the agent-ix licensing policy — no carve-outs.
