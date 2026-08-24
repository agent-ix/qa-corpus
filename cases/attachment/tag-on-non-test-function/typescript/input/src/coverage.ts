// PRODUCTION code. The shape is taken from catalog-mcp-ui/src/ElementList.tsx:20
// — a `//` comment carrying a requirement id at column 0, directly above an
// exported arrow-const.
//
// `severityOf` is a plain function, so `SymbolKind::Function`. CR-061 made
// `binds_trace_ids()` false for that kind, so the tag is not even a binding
// CANDIDATE — it is missing from the census denominator rather than counted as
// a miss. The `implements` channel needs the literal `Implements:` keyword,
// which this comment does not carry.
//
// No id is written anywhere in this header on purpose. A tag is the only thing
// in this file that names one.

// TC-001: Warning default.
export const severityOf = (finding: { severity?: string }) =>
  finding.severity ?? "warning";
