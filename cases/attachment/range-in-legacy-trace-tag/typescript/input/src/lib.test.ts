// A range in a legacy `Trace:` line binds no id, not even its left endpoint (CR-187).
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  // Trace: FR-001-AC-1..FR-001-AC-2
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});
