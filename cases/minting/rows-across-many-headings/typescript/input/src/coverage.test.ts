// Three real, correctly-tagged vitest tests, one per matrix row. The tags are
// not the defect: all three bind. Two of the rows they answer for are invisible
// to the declaration, so two of these symbols back nothing at all.
import { describe, it, expect } from "vitest";
import { trace } from "./trace";

describe("coverage", () => {
  it("covers the first criterion", () => {
    trace("TC-001");
    expect(1 + 1).toBe(2);
  });

  it("covers the second criterion", () => {
    trace("TC-002");
    expect(2 + 2).toBe(4);
  });

  it("covers the third criterion", () => {
    trace("TC-003");
    expect(3 + 3).toBe(6);
  });
});
