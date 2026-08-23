# `bench-legacy` — a relaxation variant, pending migration

**Relaxation ticket: `agent-ix/quire-rs#285`.**

This is the synthetic module the ten ported quire-rs cases were written against.
It differs from the ecosystem declaration in exactly the way FR-065 exists to
forbid:

| | this variant | the ecosystem |
|---|---|---|
| `test-case.section` | `Test Cases` | `Test Case Summary` |
| `test-case.id_column` | `ID` | `Test ID` |

**A corpus bound to this manifest cannot exhibit the defect accounting for 3,514
unminted TC ids.** It is vendored here, named, and ticketed rather than quietly
carried, because #266's scope is *porting the existing cases with no assertion
lost* — rebinding them to the real declaration changes what they assert, which is
migration work with its own before/after, not a port.

Every case on this variant is a `GAP` against the mode it appears to cover. The
bounds matrix says so; `#285` closes it.
