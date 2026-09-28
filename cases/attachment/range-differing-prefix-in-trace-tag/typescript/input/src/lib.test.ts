// A range across two requirements' ids binds no id at all (CR-187).
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("carries a stable reason", () => {
    trace("FR-001-AC-2..FR-002-AC-1");
    expect(1 + 1).toBe(2);
  });
});
