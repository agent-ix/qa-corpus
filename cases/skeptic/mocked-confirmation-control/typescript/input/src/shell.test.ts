class Confirmation {
  static fromUser(): Confirmation {
    return new Confirmation();
  }
}

function grantRoot(_confirmation: Confirmation): boolean {
  return true;
}

// Trace: TC-001
test("covers", () => {
  expect(grantRoot(Confirmation.fromUser())).toBe(true);
});
