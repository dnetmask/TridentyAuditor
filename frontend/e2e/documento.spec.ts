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

  // Panel de copia controlada (Fase 3): elaboró/revisó/aprobó visibles.
  await expect(page.getByText("Elaboró:")).toBeVisible();
  await expect(page.getByText("Aprobó:")).toBeVisible();

  // Botón Ver: abre el archivo en una pestaña nueva sin descargarlo.
  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.click('button:has-text("Ver")'),
  ]);
  await popup.waitForLoadState();
  expect(popup.url()).toContain("blob:");
});

test("un documento con área exige dos firmas: gerente de área y seguridad", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Firmas" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/ruta-sgsi");
  await page.click('.sidebar-nav a[title="Documentos"]');

  // Crear el área desde la misma pantalla.
  await page.click('button:has-text("Áreas")');
  await page.fill("#new-area", "Calidad");
  await page.click('button:has-text("Agregar")');
  await expect(page.locator(".modal strong", { hasText: "Calidad" })).toBeVisible();
  await page.click('.modal button:has-text("Cerrar")');

  await page.click('button:has-text("+ Nuevo documento")');
  const code = `PRC-E2E-${uniqueSuffix()}`;
  await page.fill("#code", code);
  await page.fill("#title", "Procedimiento con dos firmas");
  await page.selectOption("#doc-area", { label: "Calidad" });
  await page.setInputFiles("#file", {
    name: "procedimiento.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 contenido e2e dos firmas"),
  });
  await page.click('.modal button:has-text("Crear")');

  const row = page.locator("tr", { hasText: code });
  await row.click();
  await page.click('button:has-text("Enviar a revisión")');

  // Firma 1 (gerente de área — el Admin puede firmar en su lugar): esperar a
  // que la firma quede REGISTRADA (✓) — no solo el texto "pendiente", que
  // existe desde antes — para que el click siguiente no caiga en medio del
  // re-render del panel.
  await page.click('button:has-text("Firmar como gerente de área")');
  await expect(page.locator(".approval-step-done")).toContainText("Gerente de área");
  await expect(page.getByText("Seguridad de la información: pendiente")).toBeVisible();
  await expect(page.locator(".badge-in_review").first()).toBeVisible();

  // Firma 2 (seguridad de la información) publica.
  await page.getByRole("button", { name: "Aprobar", exact: true }).click();
  await expect(page.locator(".badge-approved").first()).toBeVisible();
});
