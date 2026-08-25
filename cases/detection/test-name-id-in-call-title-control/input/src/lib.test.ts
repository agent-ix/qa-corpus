// Precision control for the test-name form. One title CARRIES an id and one
// merely NAMES one in prose; only the first may bind. A form that read an id
// from anywhere in the title would mark TC-001 backed by a test that says in
// plain English that it does not verify it.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("tc-002: names the row a finding came from", () => {
    expect("TC-002").toMatch(/^TC-/);
  });

  it("does not verify tc-001, which lives in another suite", () => {
    expect(1 + 1).toBe(2);
  });
});
