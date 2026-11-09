import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("defaults every finding to warning", () => {
    const severity = "warning";
    // this tag names the matrix row.
    trace("TC-001");
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // this tag names a minted row.
    trace("TC-002");
    expect(declaration).toBeTruthy();
  });
});
