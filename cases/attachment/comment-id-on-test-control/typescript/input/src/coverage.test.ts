test("marked", () => {
  trace("TC-002");
  expect(2 + 2).toBe(4);
});

test("commented", () => {
  trace("TC-001");
  expect(1 + 1).toBe(2);
});
