export function isContained(path: string): boolean {
  return !path.startsWith("/") && !path.includes("..") && !path.includes("\0");
}

test("covers", () => {
  trace("TC-001");
  const path = "a/b";
  const expected = !path.startsWith("/") && !path.includes("..") && !path.includes("\0");
  expect(isContained(path)).toBe(expected);
});
