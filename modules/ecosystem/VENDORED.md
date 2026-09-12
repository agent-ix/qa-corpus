# `modules/ecosystem/` — the real declaration, vendored

This directory is a **module path** carrying verbatim copies of the ecosystem's
two declaring modules. It is
the module a case binds unless it names a relaxation ticket (FR-065 CON-3).

**The real declaration is TWO modules**, and this directory is a module *path*
carrying both. Vendoring only `spec-artifacts-process` was the defect
`agent-ix/quire-rs#292` records: it declares the `traceability:` model but not
`FR`, `NFR` or `TestMatrix`, so minting worked while **criteria classification
silently produced nothing** and `catch-all-universal` could not fire on any
fixture. The totals were identical either way, which is why it went unnoticed.

| Module | Source path | Pinned SHA |
|---|---|---|
| `spec-artifacts-process` | `spec_artifacts_process/` | `375fc2a9c49c37cce0f43384878b8ede16b162a3` |
| `spec-artifacts-iso` | `spec_artifacts_iso/` | `a6b1c70be8c22e9f7cb432e4410b7a3a280d0217` |

Vendored 2026-08-26 from the Project 18 tracking branches; the process
SHA refreshed 2026-09-12 for the single-`Status`-column collapse.

## Tracking status

These SHAs are tracking-branch commits, not `main` releases. The process source
now owns both `typescript-test-name-id` and the CR-118 section family; the ISO
source owns the matching `SectionNames` schema. There are no corpus-only
declaration deltas.

The process SHA moved to `375fc2a` (agent-ix/spec-artifacts-process#87), which
collapses `Coverage Status` and `Status` into one `Status` column. The two names
carried byte-identical vocabularies and were applied inconsistently across
sibling coverage tables, so the single global `traceability.status.column`
selector matched only some of them and status classification was silently
skipped on the rest. Note this commit is on the `epic/264-assurance-integration`
cohort; the process `main` does not yet carry the collapse.

## Why a copy and not a submodule

A case must be reproducible by `cd`-ing into its own `input/` and pointing the CLI
at a path (FR-065-AC-18). A nested submodule makes that invocation depend on
somebody having run `git submodule update --init` in a repository that is itself
consumed as a submodule, two levels down. The copy is the artifact; this file is
its provenance.

## The refresh ritual (FR-065-CON-4)

```
# WHOLE DIRECTORIES, not manifests. Archetypes reference their schema files
# relative to the module root, so a manifest-only copy fails registration and
# emits `undeclared-coverage-vocabulary` on every case — which is exactly the
# defect agent-ix/quire-rs#292 records.
for m in spec-artifacts-iso spec-artifacts-process; do
  src="../${m}/$(echo "$m" | tr - _)"
  rsync -a --exclude '__pycache__' --exclude '*.py' "$src/" "modules/ecosystem/$m/"
  git -C "../$m" rev-parse HEAD   # record both in the table above
done
make ci                                             # every case re-runs against the new declaration
```

Moving the SHA is **the reviewable event**. A declaration change that alters what
cases mint must show up as a diff here and as expectation diffs in the cases it
moves — which is the whole point, and the reason this is a copy with a recorded
SHA rather than a silent fetch.

## What the declaration actually says, and why it matters here

```yaml
- name: test-case
  archetype: TestMatrix
  section:
  - "*Test Case Summary*"
  - Integration Test Matrix      # NOT "Test Cases"
  id_column: Test ID             # NOT "ID"
```

CR-118's isolated, same-engine measurement was **+83 minted rows / +1 backed**;
the earlier 3,514 figure counted id-shaped strings rather than mintable cells
and is retracted by `agent-ix/quire-rs#351`. The corpus keeps the heading and
id-column faults separate so each reports the setting an author can change.

`agent-ix/quire-rs#285` migrated the last case off it and **deleted it**. Every
fixture in this corpus now binds this declaration except one, and that one binds
a variant relaxing a single axis it is itself named for
(`modules/variants/no-implements-declaration/`, `agent-ix/quire-rs#330`).
