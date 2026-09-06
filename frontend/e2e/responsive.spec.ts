import { expect, test } from "@playwright/test";
import { createTenantWithAdmin, loginAs } from "./helpers";

// Responsive: en móvil (<768px) el sidebar vive fuera de pantalla y se abre
// como cajón desde la hamburguesa; se cierra al navegar. En tablet (<1024px)
// se fuerza el riel de íconos y desaparece el botón "Contraer".
test("móvil: cajón con hamburguesa que se cierra al navegar; tablet: riel de íconos", async ({ page }) => {
  // El alta del tenant se hace en escritorio: en móvil el botón "Salir" del
  // sidebar queda fuera de pantalla y el helper no podría pulsarlo.
  const admin = await createTenantWithAdmin(page, { namePrefix: "E2E Responsive" });
  await loginAs(page, admin.email, admin.password);
  await page.waitForURL("**/panel");

  // --- Móvil ---
  await page.setViewportSize({ width: 390, height: 844 });
  const menuBtn = page.locator(".topbar-menu-btn");
  await expect(menuBtn).toBeVisible();
  await expect(page.locator(".sidebar.sidebar-mobile-open")).toHaveCount(0);

  await menuBtn.click();
  await expect(page.locator(".sidebar.sidebar-mobile-open")).toBeVisible();
  await expect(page.locator(".sidebar-backdrop")).toBeVisible();

  // Navegar desde el cajón lo cierra solo.
  await page.click('.sidebar-nav a[title="Documentos"]');
  await page.waitForURL("**/documentos");
  await expect(page.locator(".sidebar.sidebar-mobile-open")).toHaveCount(0);
  await expect(page.locator(".sidebar-backdrop")).toHaveCount(0);

  // Tocar el fondo también lo cierra.
  await menuBtn.click();
  await expect(page.locator(".sidebar-backdrop")).toBeVisible();
  await page.locator(".sidebar-backdrop").click({ position: { x: 380, y: 400 } });
  await expect(page.locator(".sidebar.sidebar-mobile-open")).toHaveCount(0);

  // --- Tablet: riel de íconos forzado, sin "Contraer" ---
  await page.setViewportSize({ width: 820, height: 1180 });
  await expect(page.locator(".sidebar.sidebar-collapsed")).toBeVisible();
  await expect(page.locator(".sidebar-collapse-toggle")).toHaveCount(0);
  await expect(menuBtn).toBeHidden();

  // --- Escritorio: vuelve el sidebar completo y el botón "Contraer" ---
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.locator(".sidebar.sidebar-collapsed")).toHaveCount(0);
  await expect(page.locator(".sidebar-collapse-toggle")).toBeVisible();
});
