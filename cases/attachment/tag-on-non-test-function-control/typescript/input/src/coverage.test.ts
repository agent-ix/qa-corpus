// The correct half of the MIXED pair: one real test, tagged on the `it` itself.
// It binds, so the census reads 1 candidate / 1 bound — a clean 100% — while the
// row the production tag names goes unbacked.
import { describe, it, expect } from "vitest";
import { severityOf } from "./coverage";

describe("coverage", () => {
  // TC-002: on the `it`, which registers an evidence symbol.
  it("names the declaration on every finding", () => {
    expect(severityOf({})).toBe("warning");
  });
});
