import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs, uniqueSuffix } from "./helpers";

// Tanda COMP (respuesta al análisis de competencia): higiene documental,
// evaluación del auditor + CAPA (avance/costo), verificación de integridad
// visible y banner guiado-vs-checklist.
test("COMP: higiene, evaluación auditor + CAPA, verificar integridad, banner", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E COMP" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");

  // Higiene documental en el panel.
  await expect(page.locator(".hygiene-grid")).toBeVisible();

  // Banner guiado-vs-checklist en la Ruta SGSI.
  await page.click('.sidebar-nav a[title="Ruta SGSI"]');
  await expect(page.locator(".guided-banner")).toBeVisible();
  await expect(page.getByText("bloquea el avance sin evidencia")).toBeVisible();

  // Auditoría: crear, completar y evaluar al auditor.
  await page.click('.sidebar-nav a[title="Auditoría"]');
  await page.click('button:has-text("+ Nueva auditoría")');
  await page.fill("#au-title", "Auditoría E2E COMP");
  await page.click('.modal button:has-text("Crear")');
  const row = page.locator("tr", { hasText: "Auditoría E2E COMP" });
  await expect(row).toBeVisible();

  // Antes de cerrar no hay evaluación; al completar aparece el puntaje.
  await expect(row.getByText("Se evalúa al cerrar")).toBeVisible();
  await row.locator("select").first().selectOption("completed");
  const scoreSelect = row.locator('select[aria-label="Puntaje del auditor"]');
  await expect(scoreSelect).toBeVisible();
  await scoreSelect.selectOption("4");

  // Hallazgo con costo estimado; el resumen CAPA lo refleja.
  await page.click('button:has-text("+ Nuevo hallazgo")');
  await page.fill("#f-description", "Falta evidencia de revisión de accesos privilegiados");
  await page.fill("#f-cost", "3500000");
  await page.click('.modal button:has-text("Crear")');
  await expect(page.getByText("Avance CAPA abierto")).toBeVisible();

  // Expandir el hallazgo muestra los campos de avance y costo.
  await page.click('tr.clickable');
  await expect(page.getByText("Avance de la acción (%)")).toBeVisible();
  await expect(page.getByText("Costo estimado")).toBeVisible();

  // Documentos: subir y verificar integridad.
  await page.click('.sidebar-nav a[title="Documentos"]');
  const code = `POL-COMP-${uniqueSuffix()}`;
  await page.click('button:has-text("+ Nuevo documento")');
  await page.waitForFunction(() => (document.querySelector("#code") as HTMLInputElement)?.value !== "");
  await page.fill("#code", code);
  await page.fill("#title", "Documento verificable");
  await page.setInputFiles("#file", {
    name: "doc.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 contenido verificable"),
  });
  await page.click('.modal button:has-text("Crear")');
  await expect(page.locator("tr", { hasText: code })).toBeVisible();

  await page.click(`tr:has-text("${code}")`);
  await page.click('button:has-text("Verificar integridad")');
  await expect(page.locator(".integrity-verdict.ok")).toBeVisible();
  await expect(page.getByText("Íntegro")).toBeVisible();
});
