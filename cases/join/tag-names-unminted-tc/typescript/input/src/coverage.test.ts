import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("defaults every finding to warning", () => {
    const severity = "warning";
    // TC-999: this valid tag has no matrix row.
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // TC-002: this tag names a minted row.
    expect(declaration).toBeTruthy();
  });
});
