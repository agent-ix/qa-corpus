---
id: TM-001
type: TestMatrix
---

## Test Cases

<!-- BOTH defects at once, which is what `agent-ix/identity` actually looks
     like. The declared heading is `Test Case Summary` and this says
     `Test Cases`; the declared id column is `Test ID` and this says
     `Test Case ID`.

     Rows 1 and 2 of #268 seeded one each and measured them separately. This
     row exists because a repository in the wild carries both, and fixing
     either alone leaves every TC id stranded — so a diagnostic that names one
     and stops sends its reader round a loop. #270 has to name BOTH. -->

| Test Case ID | Traces To | Status |
|--------------|-----------|--------|
| TC-001 | FR-001-AC-1 | 🚧 |
