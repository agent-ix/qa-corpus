// The shape is taken from quoin/tests/org-no-subprocess.test.ts:5 — a
// comment-id at column 0, after the imports, with the tests further down the
// file. The real one reads `// FR-NNN-AC-N: resolution executes no subprocess.`
//
// THE QUOTED ID IS REDACTED TO `FR-NNN-AC-N` ON PURPOSE, and restoring the real
// one re-breaks this fixture. A container's span runs to EOF, so every id
// anywhere in this file is inside it — including one quoted in THIS header to
// describe another repository's line. `agent-ix/quire-rs#312` reported it,
// correctly by its own rule and against this fixture's stated design of exactly
// one defect. The sibling fixture says the same thing as a rule: "No id is
// written anywhere in this header on purpose."
//
// MIXED on purpose — one tag at module scope beside one on the `it` itself.
import { describe, it, expect } from "vitest";

// TC-001: FR-001-AC-1 — module scope. The nearest enclosing symbol is the
// FILE's own container symbol, which `typescript.rs` emits for every module and
// spans line 1 to EOF. A container does not bind trace ids (CR-061), so TC-001
// is answered by nobody.

describe("warning default", () => {
  it("defaults every finding to warning", () => {
    expect(1 + 1).toBe(2);
  });
});

// TC-002: FR-001-AC-2 — the same tag form, on the `it`. This one attaches, and
// it is what keeps the census above the diagnostic floor.
it("names the declaration on every finding", () => {
  expect(2 + 2).toBe(4);
});
