import { expect, test } from "@playwright/test";
import { SUPER_EMAIL, SUPER_PASSWORD, loginAs } from "./helpers";

test("el Super Admin entra y llega al panel de tenants", async ({ page }) => {
  await loginAs(page, SUPER_EMAIL, SUPER_PASSWORD);
  await page.waitForURL("**/admin/tenants");
  await expect(page.getByRole("button", { name: "+ Nuevo tenant" })).toBeVisible();
});

test("una contraseña equivocada muestra el error y no navega", async ({ page }) => {
  await loginAs(page, SUPER_EMAIL, "definitivamente-no-es");
  await expect(page.locator(".alert-error")).toBeVisible();
  await expect(page).toHaveURL(/\/entrar$/);
});
