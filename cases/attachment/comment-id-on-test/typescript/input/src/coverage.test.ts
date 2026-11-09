test("marked", () => {
  trace("TC-002");
  expect(2 + 2).toBe(4);
});

// TC-001: this comment names the row, but only a marker binds.
test("commented", () => {
  expect(1 + 1).toBe(2);
});
