// The SAME production file with ONE line changed: the tag above `severityOf`
// is written in the form the production channel accepts.
//
// This is the harder control on purpose. The id-shaped annotation is still
// sitting above production code — what changed is that it now names the
// relation the symbol kind can carry. A detector written as "any declared
// trace-id form inside a symbol that does not bind trace ids" would fire here
// too, and be wrong.

// Implements: FR-001-AC-1
export const severityOf = (finding: { severity?: string }) =>
  finding.severity ?? "warning";
