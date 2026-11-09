// TC-001: still a comment, though the marker below names the same id.
test("backed and commented", () => {
  trace("TC-001");
  expect(1 + 1).toBe(2);
});
