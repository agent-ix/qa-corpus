# `modules/ecosystem/` — the real declaration, vendored

`manifest.yaml` here is a **verbatim copy** of the ecosystem's declaration. It is
the module a case binds unless it names a relaxation ticket (FR-065 CON-3).

**The real declaration is TWO modules**, and this directory is a module *path*
carrying both. Vendoring only `spec-artifacts-process` was the defect
`agent-ix/quire-rs#292` records: it declares the `traceability:` model but not
`FR`, `NFR` or `TestMatrix`, so minting worked while **criteria classification
silently produced nothing** and `catch-all-universal` could not fire on any
fixture. The totals were identical either way, which is why it went unnoticed.

| Module | Source path | Pinned SHA |
|---|---|---|
| `spec-artifacts-process` | `spec_artifacts_process/manifest.yaml` | `fa56ced6d772dc6f95a4d61bd0b813762488405d` |
| `spec-artifacts-iso` | `spec_artifacts_iso/manifest.yaml` | `3d871962b66db99a1854f40466e94ebabc7a6115` |

Vendored 2026-08-24.

## Why a copy and not a submodule

A case must be reproducible by `cd`-ing into its own `input/` and pointing the CLI
at a path (FR-065-AC-18). A nested submodule makes that invocation depend on
somebody having run `git submodule update --init` in a repository that is itself
consumed as a submodule, two levels down. The copy is the artifact; this file is
its provenance.

## The refresh ritual (FR-065-CON-4)

```
cp ../spec-artifacts-process/spec_artifacts_process/manifest.yaml \
   modules/ecosystem/spec-artifacts-process/manifest.yaml
cp ../spec-artifacts-iso/spec_artifacts_iso/manifest.yaml \
   modules/ecosystem/spec-artifacts-iso/manifest.yaml
git -C ../spec-artifacts-process rev-parse HEAD     # record both in the table above
git -C ../spec-artifacts-iso rev-parse HEAD
python3 -m pytest tests/                            # every case re-runs against the new declaration
```

Moving the SHA is **the reviewable event**. A declaration change that alters what
cases mint must show up as a diff here and as expectation diffs in the cases it
moves — which is the whole point, and the reason this is a copy with a recorded
SHA rather than a silent fetch.

## What the declaration actually says, and why it matters here

```yaml
- name: test-case
  archetype: TestMatrix
  section: Test Case Summary     # NOT "Test Cases"
  id_column: Test ID             # NOT "ID"
```

One heading name strands **3,514 TC ids across 88 repositories**. A corpus bound
to a manifest whose heading always matches cannot exhibit that defect — which is
why the synthetic module the ported cases still carry lives in
`modules/variants/bench-legacy/` under a named ticket rather than here.
