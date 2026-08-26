# `no-implements-declaration` — a declaration under test, not a relaxation

**Classification: declaration under test.**

This variant is the ecosystem declaration with **one** thing taken out:
`traceability.trace_tags.implements`.

| | this variant | the ecosystem |
|---|---|---|
| `test-case.section` | `*Test Case Summary*`, `Integration Test Matrix` | same |
| `test-case.id_column` | `Test ID` | same |
| `trace_tags.markers` | `rust-trace-attribute` | same pattern, plus python and typescript |
| `trace_tags.implements` | **absent** | `rust-implements-line`, `python-implements-line`, `typescript-implements-line` |

## Why it exists and why no ticket removes it

`cases/provenance/implements-never-asked` asserts `coverage.implements` is
`state: not_computed` — the `agent-ix/quire-rs#226` distinction between *the
engine computed this and found none* and *the engine never asked*. The engine
reaches `not_computed` only when the loaded module declares no `implements`
forms.

**[RAN]** the same input tree twice, engine `bcda5ed` / `quire` 0.30.2:

| module | `coverage.implements` |
|---|---|
| this variant | `state: not_computed`, no value, no counts |
| `modules/ecosystem` | `state: measured`, `value: 0`, `examined: 1`, `matched: 0` |

Both are correct and different. The absent declaration is the fixture's
subject, so no migration ticket exists or should be invented for it (#330).

## Why exactly one axis

`bench-legacy`, which this variant does not replace and which `#285` deleted,
relaxed **two** — the heading and the id column — on top of declaring one trace
form where the ecosystem declares five. A variant relaxing several axes cannot
say which one a payload came from. Everything here that the fixture is *not*
about is spelled the way `modules/ecosystem/spec-artifacts-process/manifest.yaml`
spells it, so the only reading this variant admits and the ecosystem does not is
the one the case is named for.

The fixture's ecosystem cell is `out-of-scope`, with the reason carried in the
derived matrix. There is no ecosystem reading of this mode for the corpus to be
missing.
