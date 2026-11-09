# `baselines/` -- per-runner ratchets

`quire-rs.json` is the detection-recall ratchet for the quire-rs runner. It records no
corpus revision: the revision a baseline was measured against is the git history of
this repository.

A `quoin.json` ratchet used to live here. Nothing in this repository, quire-rs,
quire-cli or quoin reads it, and it was last measured before the cases were reworked for
marker-only binding (CR-215), so it is deleted rather than kept as an unread number.
A runner that wants its own ratchet adds its file with the measurement that produced it.
