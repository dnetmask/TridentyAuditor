import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs, uniqueSuffix } from "./helpers";

test("el panel de entrada y el mapa de procesos muestran el estado del tenant", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Procesos" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");

  // Dashboard de entrada: cumplimiento global + tarjetas por módulo.
  await expect(page.getByText("Cumplimiento global")).toBeVisible();
  await expect(page.locator(".stat-card", { hasText: "Procesos" })).toBeVisible();

  // Crear un documento para colgarlo del proceso.
  await page.click('.sidebar-nav a[title="Documentos"]');
  await page.click('button:has-text("+ Nuevo documento")');
  const code = `POL-PRC-${uniqueSuffix()}`;
  await page.waitForFunction(() => (document.querySelector("#code") as HTMLInputElement)?.value !== "");
  await page.fill("#code", code);
  await page.fill("#title", "Documento del proceso");
  await page.setInputFiles("#file", {
    name: "doc.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 proceso e2e"),
  });
  await page.click('.modal button:has-text("Crear")');
  await expect(page.locator("tr", { hasText: code })).toBeVisible();

  // Crear un proceso y vincular el documento.
  await page.click('.sidebar-nav a[title="Procesos"]');
  await expect(page.getByText("Todavía no hay procesos", { exact: false })).toBeVisible();
  await page.click('button:has-text("+ Nuevo proceso")');
  await page.fill("#p-name", "Gestión Humana");
  await page.selectOption(".modal .control-chips select", { label: `${code} · Documento del proceso` });
  await page.click('.modal button:has-text("Crear")');

  const branch = page.locator(".process-branch", { hasText: "Gestión Humana" });
  await expect(branch).toBeVisible();
  await expect(branch.getByText("1 doc.")).toBeVisible();

  // Previsualización embebida al hacer clic en el documento del proceso.
  await branch.locator(".process-doc").first().click();
  await expect(page.locator(".doc-viewer-frame")).toBeVisible();
});
