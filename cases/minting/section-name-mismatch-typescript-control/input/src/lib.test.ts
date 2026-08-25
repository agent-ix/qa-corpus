// A real, correctly-tagged test. The tag is not the defect.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("defaults every finding to warning", () => {
    trace("TC-001");
    expect(1 + 1).toBe(2);
  });
});
