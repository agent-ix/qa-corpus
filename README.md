# qa-corpus

The controlled corpus for the `quire` / `quoin` toolchain. **Static files, read in
place, language-neutral.** Contract: [`agent-ix/quire-rs` FR-065](https://github.com/agent-ix/quire-rs/blob/main/spec/functional/FR-065-controlled-corpus-contract.md).

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
make bounds                     # the derived matrix and gap_count
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

## Layout

```
corpus.yaml          schema version, vocabularies, and the INVENTORY (intent only —
                     the case index and the matrix are DERIVED, see below)
bounds.py            derives the matrix and gap_count from the filesystem
verify.py            runs every case by its own `reproduce` and diffs expect.yaml
modules/
  ecosystem/         THE REAL declaration, vendored with its source SHA (VENDORED.md)
  variants/<id>/     relaxation variants — each names the ticket it sizes
cases/<mode>/<case>/                       ONE language
  case.yaml          id, case, issue_ref, mode, language, module, kind, findable,
                     reproduce; control_for on a control; relaxation_ticket on a
                     variant binding; pending on a case awaiting its fix
  input/ expect.yaml

cases/<mode>/<case>/                       a LANGUAGE SET
  case.yaml          everything SHARED — identity: id, case, issue_ref, mode,
                     module, kind, findable, control_for
  <language>/
    case.yaml        only what VARIES: reproduce, per-language overrides
    input/ expect.yaml

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

### Today: run `make bounds`

Run `make bounds` — these numbers are **derived, never stored**, so they cannot go
stale. Adding a fixture flips its own cell and moves the count with no edit to any
central file.

`agent-ix/quire-rs#285` migrated the last of the ported `quire-rs` cases off
`bench-legacy` — the synthetic manifest whose heading always matches — and deleted
it. Every fixture binds the vendored ecosystem declaration now, with one exception
that the matrix still reports as a `GAP`: `provenance/implements-never-asked`
asserts a metric state (`coverage.implements: not_computed`) that only a module
declaring no `implements` forms can produce, so it binds a variant relaxing that one
axis (`agent-ix/quire-rs#330`).

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

## Licence

AGPL-3.0-or-later. Per the agent-ix licensing policy — no carve-outs.
