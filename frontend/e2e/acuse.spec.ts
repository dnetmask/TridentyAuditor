import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs, uniqueSuffix } from "./helpers";

test("acuse de recibo: aprobar, distribuir al admin y marcar leído y entendido", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Acuse" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");

  // Crear y aprobar un documento (sin área = una firma).
  await page.click('.sidebar-nav a[title="Documentos"]');
  await page.click('button:has-text("+ Nuevo documento")');
  const code = `POL-ACK-${uniqueSuffix()}`;
  await page.waitForFunction(() => (document.querySelector("#code") as HTMLInputElement)?.value !== "");
  await page.fill("#code", code);
  await page.fill("#title", "Política que exige acuse");
  await page.setInputFiles("#file", {
    name: "pol.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 acuse e2e"),
  });
  await page.click('.modal button:has-text("Crear")');
  const row = page.locator("tr", { hasText: code });
  await row.click();
  await page.click('button:has-text("Enviar a revisión")');
  await page.getByRole("button", { name: "Aprobar", exact: true }).click();
  await expect(page.locator(".badge-approved").first()).toBeVisible();

  // Distribuir al propio admin (único usuario del tenant).
  await page.click('button:has-text("Distribuir…")');
  await page.locator('.modal input[type="checkbox"]').first().check();
  await page.click('.modal button:has-text("Distribuir a")');

  // Aparece el banner de "obligatorios sin leer".
  await expect(page.getByText("obligatorio", { exact: false }).first()).toBeVisible();

  // Marcar leído y entendido desde el banner.
  await page.click('.pending-item button:has-text("Marcar leído y entendido")');
  await expect(page.locator(".pending-banner")).toHaveCount(0);
});
