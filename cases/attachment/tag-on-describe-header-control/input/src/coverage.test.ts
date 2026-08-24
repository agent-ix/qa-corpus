// The SAME file with the first tag moved off the `describe(` header and onto
// the `it` inside it. Nothing else differs.
import { describe, it, expect } from "vitest";

describe("warning default", () => {
  // TC-001: FR-001-AC-1 — on the `it`, which registers a symbol.
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

// TC-002: FR-001-AC-2 — unchanged.
it("names the declaration on every finding", () => {
  expect(2 + 2).toBe(4);
});
