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
| `spec-artifacts-process` | `spec_artifacts_process/manifest.yaml` | `c197b1c0a10148164620ca0626d82ca5edd032bd` |
| `spec-artifacts-iso` | `spec_artifacts_iso/manifest.yaml` | `3d871962b66db99a1854f40466e94ebabc7a6115` |

Vendored 2026-08-24. `spec-artifacts-iso` was already at its upstream `HEAD` and
is unchanged.

## Why `spec-artifacts-process` moved from `fa56ced` to `c197b1c`

**A corpus that vendors a stale declaration cannot measure a declaration-side
fix.** `fa56ced` predates `2ed3bb9`, `feat(traceability): typescript reads a
test's own title (#68)`, so at the old pin **no declared pattern could read a
TypeScript test's name** and `cases/detection/test-name-id-in-call-title` would
have bound nothing for a reason that has nothing to do with the engine.

The refresh is measured, not assumed safe. `git diff fa56ced c197b1c --
spec_artifacts_process/manifest.yaml` is **284 lines added, 0 removed, of which
exactly 5 are not comments** — the `typescript-test-name-id` form and nothing
else. Every other file in the directory is byte-identical (`rsync
--itemize-changes` reports a content change on `manifest.yaml` alone). So the
refresh adds one TypeScript-only marker form and changes no declared behaviour
for any existing case, all 22 of which are Rust.

`spec-artifacts-process#69` also landed in this range and is comment-only in
this manifest: a written decision about five unminted id classes, with no
change to a pattern, a vocabulary or a schema.

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
  section: Test Case Summary     # NOT "Test Cases"
  id_column: Test ID             # NOT "ID"
```

One heading name strands **3,514 TC ids across 88 repositories**. A corpus bound
to a manifest whose heading always matches cannot exhibit that defect — which is
why the synthetic module the ported cases still carry lives in
`modules/variants/bench-legacy/` under a named ticket rather than here.
