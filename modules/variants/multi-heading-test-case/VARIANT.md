# `multi-heading-test-case` — a declaration under test

**Classification: declaration under test.** A corpus-owned fixture module, not a copy of
any ecosystem module. `agent-ix/quire-rs#272` made `TraceTarget.section` accept a list or
a pattern; the installed `spec-artifacts-process` declares one heading, so the engine
behaviour needs a declaration that uses it. This one declares `*Test Case Summary*` and
nothing else the case does not need. Used by `cases/minting/rows-across-many-headings`.
