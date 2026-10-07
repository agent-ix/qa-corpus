// A range written inside a trace tag binds no id at all (CR-187).
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("defaults every finding to warning", () => {
    trace("FR-001-AC-1..FR-001-AC-2");
    expect(1 + 1).toBe(2);
  });
});
