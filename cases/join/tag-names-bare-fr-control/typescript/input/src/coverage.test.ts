// The SAME file with FOUR CHARACTERS added to one tag: the bare requirement id
// becomes the criterion id the declaration mints. Nothing else differs — same
// two tests, same comment form, same position in the body, same sibling tag.
//
// That is the whole repair, and it is why the pair is worth having: the failure
// case is not a missing tag, a misplaced tag or an unreadable tag. It is a tag
// the engine reads perfectly and joins to nothing.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("defaults every finding to warning", () => {
    const severity = "warning";
    // every finding defaults to warning.
    trace("TC-001", "FR-001-AC-1");
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // the row's own minted id, which the declaration can join.
    trace("TC-002");
    expect(declaration).toBeTruthy();
  });
});
