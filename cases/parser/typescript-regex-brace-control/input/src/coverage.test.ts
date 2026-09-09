test("regex content does not change block depth", () => {
  trace("TC-001");
  const branch = /else if \(x\) x[\s\S]*done/;
  expect(branch.test("else if (x) x done")).toBe(true);
});
