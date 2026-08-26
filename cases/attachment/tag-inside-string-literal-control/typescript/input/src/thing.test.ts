// The control: the same two tests, and the tag is a tag.

test("real", () => {
  // Trace: TC-001
  expect(true).toBe(true);
});

test("carries an example", () => {
  // ONE LINE MOVED. The tag is in a comment, where a legacy form belongs, and
  // the template literal below carries no tag-shaped text at all. So this test
  // really does verify TC-002 and the row is backed — which is what makes the
  // pair discriminate: the mask must blank a string's CONTENTS and leave
  // comments alone, and a mask that blanked both would make this control red.
  // Trace: TC-002
  const example = `
        an ordinary fixture string
    `;
  expect(example).toContain("ordinary");
});
