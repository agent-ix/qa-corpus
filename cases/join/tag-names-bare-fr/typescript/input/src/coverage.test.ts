// The shape is taken from filament-ui-shared/tests/useArchetypeNav.test.ts:48 —
// a `//` comment carrying a BARE requirement id, inside the `it` body, on the
// assertion it justifies.
//
// The tag BINDS. The marker admits `FR-\d+` and the enclosing
// symbol is a test registration, so this is a healthy binding by every measure
// the engine has: the census counts it, and it counts it as bound. What it binds
// to is an id the declaration never minted.
//
// MIXED on purpose — one bare requirement id beside one minted test-case id.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("defaults every finding to warning", () => {
    const severity = "warning";
    // every finding defaults to warning.
    trace("FR-001");
    expect(severity).toBe("warning");
  });

  it("names the declaration on every finding", () => {
    const declaration = "traceability.trace_tags";
    // the row's own minted id, which the declaration can join.
    trace("TC-002");
    expect(declaration).toBeTruthy();
  });
});
