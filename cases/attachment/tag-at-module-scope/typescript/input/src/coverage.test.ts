// A citation written as a module-level comment after the imports, with a
// correctly marked sibling test. The comment is prose: only a marker binds, so
// the test it was meant for is answered by nobody, and the advisory names it.
import { describe, it, expect } from "vitest";

// TC-001 -- module scope.

describe("warning default", () => {
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

it("names the declaration on every finding", () => {
  trace("TC-002");
  expect(2 + 2).toBe(4);
});
