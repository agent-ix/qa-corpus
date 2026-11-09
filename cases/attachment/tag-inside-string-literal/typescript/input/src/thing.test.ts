// Seeded: comment-shaped text inside a string literal on a test's own declaration.

test("real", () => {
  trace("TC-001");
  expect(true).toBe(true);
});

test("// TC-002: not a tag", () => {
  expect(true).toBe(true);
});
