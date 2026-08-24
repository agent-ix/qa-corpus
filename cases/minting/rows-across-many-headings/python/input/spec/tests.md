---
id: TM-001
type: TestMatrix
---

<!-- The declared heading is `Test Case Summary`, and it is HERE — correctly
     spelled, with the declared `Test ID` column. Rows 1-3 of #268 seeded a
     wrong heading or a wrong column; nothing here is misspelled.

     The defect is that the rows are spread across SEVERAL headings and the
     declaration names ONE. `agent-ix/identity` carries roughly thirty. Only
     the rows under the declared heading mint; every other row is invisible,
     and the denominator silently becomes "the rows that happened to sit under
     one heading" rather than "the rows this document declares".

     This is the shape agent-ix/quire-rs#272 fixes by letting
     `TraceTarget.section` accept a list or a pattern. -->

## Test Case Summary

| Test ID | Traces To | Status |
|---------|-----------|--------|
| TC-001 | FR-001-AC-1 | 🚧 |

## Test Case Summary — Authentication

| Test ID | Traces To | Status |
|---------|-----------|--------|
| TC-002 | FR-001-AC-2 | 🚧 |

## Test Case Summary — Authorization

| Test ID | Traces To | Status |
|---------|-----------|--------|
| TC-003 | FR-001-AC-3 | 🚧 |
