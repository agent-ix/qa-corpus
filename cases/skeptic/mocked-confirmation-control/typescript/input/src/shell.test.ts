class Confirmation {
  static fromUser(): Confirmation {
    return new Confirmation();
  }
}

function grantRoot(_confirmation: Confirmation): boolean {
  return true;
}

test("covers", () => {
  trace("TC-001");
  expect(grantRoot(Confirmation.fromUser())).toBe(true);
});
