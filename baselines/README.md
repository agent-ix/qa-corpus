# `baselines/` — per-runner ratchets

`quire-rs.json` and `quoin.json` are the independent detection-recall ratchets
for the two runners. The measurement exporter derives the `detection.recall`
observations from them. They record no corpus revision: the revision a
baseline was measured against is the git history of this repository.

Baselines live here rather than in either tool's `bench/` so that one corpus
change moves both ratchets in one reviewable diff.
