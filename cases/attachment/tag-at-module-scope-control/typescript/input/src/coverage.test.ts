// The SAME file with the module-scope citation written as the marker on the
// `it` it names. Nothing else differs: same two tests, same two ids.
import { describe, it, expect } from "vitest";

describe("warning default", () => {
  it("defaults every finding to warning", () => {
    trace("TC-001");
    expect(1 + 1).toBe(2);
  });
});

it("names the declaration on every finding", () => {
  trace("TC-002");
  expect(2 + 2).toBe(4);
});
