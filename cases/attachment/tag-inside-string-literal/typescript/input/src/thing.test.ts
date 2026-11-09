// Seeded: tag-shaped text inside a string literal, in a test's own span.

test("real", () => {
  trace("TC-001");
  expect(true).toBe(true);
});

test("carries an example", () => {
  // THE DEFECT SHAPE. The text below is DATA this test asserts about, not a
  // tag on this test: no id in it binds, and none is reported as a misplaced
  // citation, because a string literal is not an annotation.
  const example = `
        Trace: TC-002
    `;
  expect(example).toContain("Trace");
});
