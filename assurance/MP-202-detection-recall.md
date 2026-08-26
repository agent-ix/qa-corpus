---
id: MP-202
title: Controlled-corpus detection recall
type: MeasurementPlan
status: active
owner: qa-corpus-maintainers
stage: ratchet
metric: detection.recall
definition_version: detection-recall-v1
relationships: []
---

# Controlled-corpus detection recall

## Decision Objective

Show exactly which validator behaviors work and which fail without allowing a
strong language, failure family, or shallow finding to hide a blind one.

## Population and Scope

Include every `findable: true`, `kind: failure` case. Partition observations by
grading level (L1/L2/L3), mode, and language. Never average partitions.

## Measure Definition

L1 requires the expected finding channel and token. L2 additionally requires
the expected locus. L3 additionally requires every expected actionable message
fragment. A case lacking ground truth for a deeper level does not reach that
level; this makes missing assertions visible instead of treating them as a pass.

Each observation reports `reached`, `population`, the exact missed case ids,
and `bounds.gap_count`. The gap count is repeated beside every score because a
perfect score over unrepresented cells is not a complete claim.

## Collection and Provenance

Record the corpus revision, declaration digest, runner/scorer revision, engine
identity and raw case-level evidence. The Quire and Quoin runners retain
separate baselines because they exercise different production surfaces.

## Environment and Sampling

Run the complete static corpus through real production commands. Exclude only
cases explicitly marked non-findable; pending cases remain visible but are not
silently scored as working.

## Interpretation and Limitations

Recall measures whether seeded failures are found. It does not measure false
positives; controls and the corpus differential gate do that. A low deeper-level
score can mean either weak tool output or absent deeper ground truth, and the
miss list identifies the exact cases requiring review.

## Comparison and Enforcement

Compare only identical definition versions and partition populations. A lower
rate fails the local gate. A higher rate is retained by the explicit baseline
update workflow; population changes are incomparable until reviewed.
