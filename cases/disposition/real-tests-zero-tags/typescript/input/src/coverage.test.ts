// Two real vitest tests and not one trace tag anywhere in the tree. The shape is
// taken from agent-pty/tests/session.test.ts, a real suite with no tag of any
// declared form in it. That repository is one of 150 with test files and no
// binding tag at all.
//
// NOT MIXED, deliberately. Every other attachment and join fixture in this
// corpus pairs a defective tag with a correct one, because a degenerate
// all-defective tree fires `no-symbol-bound` for a reason that holds in no real
// repository. Here the degenerate tree IS the population: the authoring is
// absent, that is the whole disposition, and `no-symbol-bound` firing is the
// correct answer rather than an artefact of the fixture.
//
// No id is written anywhere in this file on purpose.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("defaults every finding to warning", () => {
    const severity = "warning";
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    expect(declaration).toBeTruthy();
  });
});
