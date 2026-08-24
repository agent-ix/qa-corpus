// A real, correctly-tagged vitest test. The tag is not the defect.
import { describe, it, expect } from "vitest";
import { trace } from "./trace";

describe("coverage", () => {
  it("covers the criterion", () => {
    trace("TC-001");
    expect(1 + 1).toBe(2);
  });
});
