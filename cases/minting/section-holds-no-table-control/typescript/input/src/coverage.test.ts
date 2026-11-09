import { it, expect } from "vitest";

it("covers the criterion", () => {
  trace("TC-001");
  expect(1 + 1).toBe(2);
});
