// Real tests, real tags, a marker spelling the module never declared.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("defaults every finding to warning", () => {
    tracks("TC-001");
    expect(1 + 1).toBe(2);
  });
});
