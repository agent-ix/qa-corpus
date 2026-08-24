// The shape is verbatim from ix-ui/packages/semantic/tests/glyphs.test.ts:100
// — a comment-id above the `describe(` header, with the work in an `it` inside.
// Re-measured for #273: 162 such tag lines across 18 repo roots (138 blocks).
// An earlier count of 209/9 in this file did not reproduce.
import { describe, it, expect } from "vitest";

// TC-001: FR-001-AC-1 — the tag is on the BLOCK header. Since #273 that header
// DOES register a symbol — a `Container` named by its title — and the tag still
// binds nothing, because a Container cannot reach the `verifies` binder
// (`trace.rs` returns at the `carries_implements()` branch). So TC-001 is
// answered by nobody, for a reason one layer deeper than this comment used to
// say. #312 is the ticket that decides whether it should bind.
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
