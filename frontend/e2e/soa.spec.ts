import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs } from "./helpers";

test("instanciar el SoA crea las entradas de la norma del tenant", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E SoA" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");

  await page.click('.sidebar-nav a[title="SoA"]');
  await expect(page.getByText("Declaración de Aplicabilidad")).toBeVisible();

  await page.click('button:has-text("Comenzar SoA")');

  // ISO 27001: 4 dominios (temas) del Anexo A con sus conteos de aplicables.
  const domains = page.locator(".domain-block");
  await expect(domains).toHaveCount(4);
  await expect(page.locator(".domain-count").first()).toContainText("aplicables");
});
