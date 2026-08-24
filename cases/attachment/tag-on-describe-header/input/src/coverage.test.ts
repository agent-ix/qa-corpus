// The shape is verbatim from ix-ui/packages/semantic/tests/glyphs.test.ts:100
// — a comment-id above the `describe(` header, with the work in an `it` inside.
// 209 occurrences across 9 repo roots write it this way.
import { describe, it, expect } from "vitest";

// TC-001: FR-001-AC-1 — the tag is on the BLOCK header, which registers no
// symbol at all. `typescript.rs` accepts only `test` and `it`, so this tag
// attaches to nothing and TC-001 is answered by nobody.
describe("warning default", () => {
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

// TC-002: FR-001-AC-2 — the same tag form, one line lower, on the `it`. This
// one attaches, and it is what keeps the census above the floor.
it("names the declaration on every finding", () => {
  expect(2 + 2).toBe(4);
});
