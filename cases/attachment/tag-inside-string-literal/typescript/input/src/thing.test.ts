// Seeded: a legacy trace form inside a string literal, in a test's own span.

test("real", () => {
  // Trace: TC-001
  expect(true).toBe(true);
});

test("carries an example", () => {
  // THE DEFECT. The legacy textual form below is DATA this test asserts about,
  // not a tag on this test. Rust masks string contents before matching legacy
  // forms; TypeScript did not, so `TC-002` bound here and the row read as
  // verified by a test that never touches it.
  const example = `
        Trace: TC-002
    `;
  expect(example).toContain("Trace");
});
