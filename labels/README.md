# `labels/` — hand-labelled ground truth

One file per case that seeds a labelled defect. Each carries the defect's id,
family, location, whether it is `findable`, the finding it should produce, and
the command that produces it.

## Provenance

These are **quoin's adjudications**, carried over verbatim when its nine
generated tier-1 corpora became static cases (`agent-ix/quoin#227`) — not new
guesses. The one exception is re-adjudicated in place and says so:
`wrong-type-cell` seeded a value that was undeclared only under the synthetic
module, so the port had to re-seed it and re-confirm the label.

That is the risk this directory carries: **a label is prose about a run, and
nothing recomputes it.** `confirmed_at` records the engine it was last checked
against. When it disagrees with a real run, the label is what is wrong — that
has now happened twice on the same file.

## What reads them

Nothing here, yet. `quoin` scores finding quality against these; `quire-rs`
grades detection from each case's `expect.yaml`. Same cases, two questions,
two answer keys — which is deliberate: #264 is explicit that folding the two
programmes together is how a fourth conflated number gets created.
