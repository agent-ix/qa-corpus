// The control for `range-differing-prefix-in-trace-tag`: each id tagged separately.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("carries a stable reason", () => {
    trace("FR-001-AC-2");
    expect(1 + 1).toBe(2);
  });

  it("reports every range", () => {
    trace("FR-002-AC-1");
    expect(1 + 1).toBe(2);
  });
});
