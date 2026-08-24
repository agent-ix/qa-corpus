// The SAME file with the module-scope tag moved onto the `it` it names.
// Nothing else differs: same two tests, same two ids, same comment form.
import { describe, it, expect } from "vitest";

describe("warning default", () => {
  // TC-001: FR-001-AC-1 — on the `it`, which registers an evidence symbol.
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

// TC-002: FR-001-AC-2 — unchanged.
it("names the declaration on every finding", () => {
  expect(2 + 2).toBe(4);
});
