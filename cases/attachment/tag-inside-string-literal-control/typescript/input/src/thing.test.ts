// The control: the same two tests, and the tag is a marker.

test("real", () => {
  trace("TC-001");
  expect(true).toBe(true);
});

test("carries an example", () => {
  // ONE LINE MOVED. The id is in a marker, where it binds, and the template
  // literal below carries no tag-shaped text at all. So this test really does
  // verify the second row and it is backed.
  trace("TC-002");
  const example = `
        an ordinary fixture string
    `;
  expect(example).toContain("ordinary");
});
