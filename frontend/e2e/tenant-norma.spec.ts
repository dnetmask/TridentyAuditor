import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs } from "./helpers";

test("un tenant CNO-1960 ve la Ruta CNO, no la Ruta SGSI", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, {
    frameworkLabel: "Guía de Ciberseguridad — Consejo Nacional de Operación (CNO)",
    namePrefix: "E2E CNO",
  });

  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/ruta-sgsi");

  await expect(page.locator('.sidebar-nav a[title="Ruta CNO"]')).toBeVisible();
  await expect(page.locator("h1")).toHaveText("Ruta CNO");
  await expect(page.getByRole("button", { name: /Comenzar ciclo de cumplimiento CNO/ })).toBeVisible();
});

test("un tenant ISO ve la Ruta SGSI clásica", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E ISO" });

  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/ruta-sgsi");

  await expect(page.locator('.sidebar-nav a[title="Ruta SGSI"]')).toBeVisible();
  await expect(page.locator("h1")).toHaveText("Ruta SGSI");
});
