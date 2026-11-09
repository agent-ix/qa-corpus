// The SAME production file with the tag above `severityOf` written in the form
// the production channel accepts (the arrow declaration is rewrapped into an
// `implementing(...)(fn)` call, so two lines become three).
//
// This is the harder control on purpose. The id-shaped annotation is still
// sitting above production code — what changed is that it now names the
// relation the symbol kind can carry. A detector written as "any declared
// trace-id form inside a symbol that does not bind trace ids" would fire here
// too, and be wrong.

export const severityOf = implementing("FR-001-AC-1")(
  (finding: { severity?: string }) => finding.severity ?? "warning",
);
