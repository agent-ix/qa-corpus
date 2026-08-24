// The trace id is in the `it(...)` TITLE and nowhere else. No `trace()` call,
// no comment marker, no `Trace:` line — this is how 81% of one repo's tests
// are written, and the declaration has no TypeScript form that reads it.
//
// `rust-test-name-id` exists and is rust-only. `spec-artifacts-process#68` adds
// the TypeScript equivalent.
import { describe, it, expect } from "vitest";

describe("coverage", () => {
  it("TC-001: every finding defaults to warning", () => {
    expect(1 + 1).toBe(2);
  });
});
