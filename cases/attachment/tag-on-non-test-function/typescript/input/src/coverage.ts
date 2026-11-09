// PRODUCTION code carrying a requirement citation as a comment directly above
// the function it describes. A production function binds no trace id and the
// comment is prose, so the advisory names the function and its kind.

// TC-001: Warning default.
export const severityOf = (finding: { severity?: string }) =>
  finding.severity ?? "warning";
