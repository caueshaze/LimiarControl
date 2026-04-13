import { test } from "@playwright/test";

test.describe.skip("combat authority — requires frontend runtime", () => {
  test("only LimiarControl can advance turn", () => {});
  test("rejects combat advance from player socket", () => {});
});
