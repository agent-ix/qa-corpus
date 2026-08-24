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
| `spec-artifacts-process` | `spec_artifacts_process/manifest.yaml` | `62d691f` (`feat/68-typescript-test-name-form`) |
| `spec-artifacts-iso` | `spec_artifacts_iso/manifest.yaml` | `3d871962b66db99a1854f40466e94ebabc7a6115` |

Vendored 2026-08-24.

## Two ways this copy is AHEAD of the SHA it names — read them before trusting it

1. **`typescript-test-name-id` is on a BRANCH, not on `main`.** `62d691f` is
   `agent-ix/spec-artifacts-process#71`, open against `main`. The SHA is recorded
   rather than the branch name because a branch moves; repoint to the squash
   commit when #71 merges.

2. **The `section:` widening is in NO spec-artifacts-process commit at all.**
   `test-case` and `traces-to` here declare
   `section: ["*Test Case Summary*", Integration Test Matrix]`, while every ref
   of that repository — checked across `refs/heads` and `refs/remotes` — still
   declares the single name `Test Case Summary`. It was authored corpus-side by
   `d272ad7` ("#272 landed — rows across many headings mint") and never
   upstreamed. So this file is not a verbatim copy of any commit, and the CR-118
   half of it has no home in the module it claims to vendor. Flagged, not
   normalised: fixing it means an upstream ticket, and doing it silently here
   would move what every case mints.

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
