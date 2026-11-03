test("regex content does not change block depth", () => {
  trace("TC-001");
  const branch = /else if \(x\) \{[\s\S]*done/;
  expect(branch.test("else if (x) { done")).toBe(true);
});
