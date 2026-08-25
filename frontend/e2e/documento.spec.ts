import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs, uniqueSuffix } from "./helpers";

test("ciclo completo de un documento: crear → enviar a revisión → aprobar", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Docs" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/ruta-sgsi");

  await page.click('.sidebar-nav a[title="Documentos"]');
  await page.click('button:has-text("+ Nuevo documento")');

  const code = `POL-E2E-${uniqueSuffix()}`;
  await page.fill("#code", code);
  await page.fill("#title", "Política de seguridad E2E");
  await page.setInputFiles("#file", {
    name: "politica.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 contenido e2e"),
  });
  await page.click('.modal button:has-text("Crear")');

  const row = page.locator("tr", { hasText: code });
  await expect(row).toBeVisible();
  await expect(row.getByText("Borrador")).toBeVisible();

  await row.click(); // abre el detalle con las acciones por versión
  await page.click('button:has-text("Enviar a revisión")');
  await page.click('button:has-text("Aprobar")');
  await expect(page.locator(".badge-approved").first()).toBeVisible();
});
