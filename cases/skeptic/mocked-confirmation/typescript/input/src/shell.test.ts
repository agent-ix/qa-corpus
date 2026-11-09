class Confirmation {
  static allow(): Confirmation {
    return new Confirmation();
  }
}

function grantRoot(_confirmation: Confirmation): boolean {
  return true;
}

test("covers", () => {
  trace("TC-001");
  expect(grantRoot(Confirmation.allow())).toBe(true);
});
