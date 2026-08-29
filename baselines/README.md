# `baselines/` — per-runner ratchets

`quire-rs.json` and `quoin.json` are the independent detection-recall ratchets
written by the two real runners. They land only from measured executions; a
baseline written before a runner exists is a number with no measurement behind
it, which is the defect this corpus was built to end.

Baselines live here rather than in either tool's `bench/` so that one corpus
change moves both ratchets in one reviewable diff.
