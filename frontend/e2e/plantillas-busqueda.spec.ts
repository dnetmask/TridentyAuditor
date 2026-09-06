import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs, uniqueSuffix } from "./helpers";

// PDF real mínimo con texto extraíble (para que la búsqueda por contenido lo indexe).
// Un %PDF de juguete no tiene capa de texto, así que usamos un .txt como contenido.
test("plantillas y búsqueda de contenido en documentos", async ({ page }) => {
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E F5b" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");
  await page.click('.sidebar-nav a[title="Documentos"]');

  // Subir una plantilla.
  await page.click('button:has-text("Plantillas")');
  await page.fill("#tpl-name", "Plantilla de política");
  await page.setInputFiles("#tpl-file", {
    name: "plantilla.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Encabezado estándar del SGSI de Netmask"),
  });
  await page.click('.modal button:has-text("Subir plantilla")');
  await expect(page.locator(".modal strong", { hasText: "Plantilla de política" })).toBeVisible();
  await page.click('.modal button:has-text("Cerrar")');

  // Crear un documento con contenido buscable (archivo de texto).
  await page.click('button:has-text("+ Nuevo documento")');
  const code = `POL-F5B-${uniqueSuffix()}`;
  await page.waitForFunction(() => (document.querySelector("#code") as HTMLInputElement)?.value !== "");
  await page.fill("#code", code);
  await page.fill("#title", "Documento con contenido");
  await page.setInputFiles("#file", {
    name: "contenido.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("El plan de continuidad del negocio se activa ante un ciberataque grave"),
  });
  await page.click('.modal button:has-text("Crear")');
  await expect(page.locator("tr", { hasText: code })).toBeVisible();

  // Buscar por una palabra que SOLO está en el contenido, no en el título.
  await page.fill('.content-search input[type="search"]', "continuidad ciberataque");
  await page.click('button:has-text("Buscar en contenido")');
  await expect(page.getByText("resultado", { exact: false })).toBeVisible();
  await expect(page.locator("tr", { hasText: code })).toBeVisible();

  // Limpiar la búsqueda vuelve a la lista filtrada.
  await page.click('button:has-text("Limpiar")');
  await expect(page.locator(".filter-bar")).toBeVisible();
});
