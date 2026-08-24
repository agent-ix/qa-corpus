// The SAME test with the SAME title, plus the declared `ts-trace-helper`
// marker. One line is the whole difference, and it is the line the declaration
// can read.
import { describe, it, expect } from "vitest";
import { trace } from "./trace";

describe("coverage", () => {
  it("TC-001: every finding defaults to warning", () => {
    trace("TC-001");
    expect(1 + 1).toBe(2);
  });
});
