// The shape is taken from identity/tests/test_tenant_auth_policy.py:195, in
// TypeScript: a `//` comment carrying an id an `## Invariants` table declares.
//
// The tag BINDS. `typescript-comment-id` admits the sub-id segment, the
// enclosing symbol is a test registration, and the census counts it as bound.
// What it binds to is an id no target mints, because `## Invariants` is a
// heading NEITHER module declares: not in the ISO `FR` skeleton, not in either
// manifest. 15 repositories author it anyway, 129 rows, and its table is the
// `Constraints` table under a different name.
//
// MIXED on purpose — one undeclared-section id beside one minted test-case id.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("carries the declared severity", () => {
    const severity = "warning";
    // FR-001-INV-1: the declared severity is the one carried.
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // TC-002: the row's own minted id, which the declaration can join.
    expect(declaration).toBeTruthy();
  });
});
