// A citation written above the `describe(` header, with the work in an `it`
// inside, and a correctly marked sibling. The header registers a suite symbol
// that binds nothing, and the comment is prose in any case: only a marker binds.
import { describe, it, expect } from "vitest";

// TC-001 -- the citation is on the BLOCK header.
describe("warning default", () => {
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

it("names the declaration on every finding", () => {
  trace("TC-002");
  expect(2 + 2).toBe(4);
});
