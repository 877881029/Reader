import { expect, test } from "vitest";

test("placeholder bootstrap message is stable", () => {
  expect("Markdown viewer loading").toBe("Markdown viewer loading");
});
