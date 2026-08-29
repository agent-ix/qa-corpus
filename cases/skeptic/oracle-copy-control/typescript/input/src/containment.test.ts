export function isContained(path: string): boolean {
  return !path.startsWith("/") && !path.includes("..") && !path.includes("\0");
}

// Trace: TC-001
test("covers", () => {
  const path = "a/b";
  const expected = true;
  expect(isContained(path)).toBe(expected);
});
