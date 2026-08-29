class Confirmation {
  static allow(): Confirmation {
    return new Confirmation();
  }
}

function grantRoot(_confirmation: Confirmation): boolean {
  return true;
}

// Trace: TC-001
test("covers", () => {
  expect(grantRoot(Confirmation.allow())).toBe(true);
});
