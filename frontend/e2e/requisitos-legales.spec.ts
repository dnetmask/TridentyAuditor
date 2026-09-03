import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs } from "./helpers";

test("la matriz legal registra un requisito y calcula el nivel de cumplimiento", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Legal" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/ruta-sgsi");

  await page.click('.sidebar-nav a[title="Requisitos legales"]');
  await expect(page.getByText("La matriz está vacía", { exact: false })).toBeVisible();

  await page.click('button:has-text("+ Nuevo requisito")');
  await page.selectOption("#req-type", "law");
  await page.fill("#req-name", "Ley 1581 de 2012");
  await page.fill("#req-issuer", "Congreso de Colombia");
  await page.fill("#req-topic", "Protección de datos personales");
  await page.click('.modal button:has-text("Crear")');

  const row = page.locator("tr", { hasText: "Ley 1581 de 2012" });
  await expect(row).toBeVisible();

  // Calificar como "Cumple" recalcula el nivel de cumplimiento de la matriz.
  await row.locator("select").selectOption("compliant");
  await expect(page.getByText("Nivel de cumplimiento:")).toBeVisible();
  await expect(page.getByText("100%")).toBeVisible();
});
