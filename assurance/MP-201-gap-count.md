---
id: MP-201
title: Controlled-corpus gap count
type: MeasurementPlan
status: active
owner: qa-corpus-maintainers
stage: ratchet
metric: bounds.gap_count
definition_version: bounds.gap-count-v1
relationships: []
---

# Controlled-corpus gap count

## Decision Objective

Show which declared mode-language cells have no valid case so missing test
coverage cannot be mistaken for working behavior.

## Population and Scope

Include every cell in `corpus.yaml`'s bounds matrix. Each cell is covered,
pending, out of scope with a reason, or GAP.

## Measure Definition

`bounds.gap_count` is the count of cells in state GAP, definition
`bounds.gap-count-v1`. It is a count, never a ratio; retain the named gap list
and pending list with the scalar.

## Collection and Provenance

Derive from the validated filesystem inventory. Record corpus revision,
inventory digest, reader version, module-source digests, timestamp, and raw
bounds output.

## Environment and Sampling

Run over the complete corpus tree. A missing or unreadable case is an error,
not an exclusion.

## Interpretation and Limitations

A lower count means fewer declared holes, not better detector recall. Converting
a cell to out-of-scope is a visible policy decision, not test coverage.

## Comparison and Enforcement

Ratchet only under the same matrix definition. A matrix or definition change is
incomparable until reviewed; never render it as a bare improvement or regression.
