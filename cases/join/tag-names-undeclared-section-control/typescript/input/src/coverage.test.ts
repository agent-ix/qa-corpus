// THE SAME FILE WITH ONE TOKEN CHANGED: the id declared by the `## Invariants`
// table becomes the id declared by `## Acceptance Criteria`. Nothing else
// differs — same two tests, same comment form, same position in the body, same
// sibling tag, same spec tree, same census.
//
// That is the whole repair, and it is why the pair is worth having. The failure
// case is not a missing tag, a misplaced tag or an unreadable tag: both ids are
// authored table rows with an `ID` column, in the same document, read by the
// same form. One id class is minted and the other is not.

import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("carries the declared severity", () => {
    const severity = "warning";
    // FR-001-AC-1: the declared severity is the one carried.
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // TC-002: the row's own minted id, which the declaration can join.
    expect(declaration).toBeTruthy();
  });
});
