# `multi-heading-test-case` — a declaration under test

**Classification: declaration under test.** A corpus-owned fixture module, not a copy of
any ecosystem module. `agent-ix/quire-rs#272` made `TraceTarget.section` accept a list or
a pattern; the multi-heading declaration (spec-artifacts-process #70, commit 995288d) exists only on
the upstream branch epic/264-assurance-integration and is NOT in the released module. The
installed `spec-artifacts-process` declares one heading and so strands rows under sibling
headings; this variant declares `*Test Case Summary*` and nothing else the case does not need. Used by `cases/minting/rows-across-many-headings`.
