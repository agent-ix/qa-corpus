# `baselines/` — per-runner ratchets

Empty by design, and tracked so a clone gets the directory.

`quire-rs.json` and `quoin.json` land when each runner first scores the corpus
(#267 and quoin#227). A baseline written before a runner exists is a number with
no measurement behind it, which is the defect this whole corpus was built to end.

Baselines live here rather than in either tool's `bench/` so that one corpus
change moves both ratchets in one reviewable diff.
