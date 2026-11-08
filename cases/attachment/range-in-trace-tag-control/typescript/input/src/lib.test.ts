// The control for `range-in-trace-tag`: each id tagged separately.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("defaults every finding to warning", () => {
    trace("TC-001", "FR-001-AC-1");
    expect(1 + 1).toBe(2);
  });

  it("carries a stable reason", () => {
    trace("TC-002", "FR-001-AC-2");
    expect(1 + 1).toBe(2);
  });
});
