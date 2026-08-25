// The id lives in the call's own title string and nowhere else. 476 of
// filament-ide-rs's 587 `it()`/`test()`/`describe()` sites are written this
// way — 81% of that repository's UI evidence, in one consistent convention.
import { describe, expect, it } from "vitest";

describe("the coverage rollup", () => {
  it("tc-001: defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });

  it("tc-002: names the row a finding came from", () => {
    expect("TC-002").toMatch(/^TC-/);
  });
});
