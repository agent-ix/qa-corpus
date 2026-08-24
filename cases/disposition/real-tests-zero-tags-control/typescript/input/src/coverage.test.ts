// The SAME two tests with a tag added to each, in the form the declaration
// reads. Nothing else differs: same titles, same bodies, same assertions.
//
// This is the disposition the failure case must be told apart from. Both trees
// have real tests; one has been authored against the matrix and one has not.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  // TC-001: the row this test answers.
  it("defaults every finding to warning", () => {
    const severity = "warning";
    expect(severity).toBe("warning");
  });

  // TC-002: the row this test answers.
  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    expect(declaration).toBeTruthy();
  });
});
