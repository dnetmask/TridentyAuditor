import { expect, type Page } from "@playwright/test";

export const SUPER_EMAIL = process.env.E2E_SUPER_EMAIL ?? "admin@netmask.co";
export const SUPER_PASSWORD = process.env.E2E_SUPER_PASSWORD ?? "supersecret123";

export function uniqueSuffix(): string {
  return `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

export async function loginAs(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/entrar");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click('button:has-text("Ingresar")');
}

export async function loginAsSuperAdmin(page: Page): Promise<void> {
  await loginAs(page, SUPER_EMAIL, SUPER_PASSWORD);
  await page.waitForURL("**/admin/tenants");
}

export interface TenantAdmin {
  email: string;
  password: string;
  tenantName: string;
}

/** Crea tenant + su primer admin desde el panel de Super Admin y cierra sesión. */
export async function createTenantWithAdmin(
  page: Page,
  opts: { frameworkLabel?: string; namePrefix?: string } = {},
): Promise<TenantAdmin> {
  const suffix = uniqueSuffix();
  const tenantName = `${opts.namePrefix ?? "E2E Tenant"} ${suffix}`;
  const admin: TenantAdmin = {
    email: `admin-${suffix}@e2e.example.com`,
    password: "tenantpass123",
    tenantName,
  };

  await loginAsSuperAdmin(page);
  await page.click('button:has-text("+ Nuevo tenant")');
  await page.waitForSelector("#t-framework");
  await page.fill("#t-name", tenantName);
  await page.fill("#t-slug", `e2e-${suffix}`);
  // Siempre explícito: el select muestra la primera norma de la lista por
  // defecto, así que confiar en el default haría al test depender del orden
  // en que la API liste los frameworks.
  await page.selectOption("#t-framework", { label: opts.frameworkLabel ?? "ISO/IEC 27001:2022" });
  await page.click('.modal button:has-text("Crear")');

  await page.waitForSelector('h2:has-text("Admin del tenant")');
  await page.fill("#ta-email", admin.email);
  await page.fill("#ta-name", "Admin E2E");
  await page.fill("#ta-password", admin.password);
  await page.click('button:has-text("Crear admin")');
  await expect(page.getByText("Cuenta creada")).toBeVisible();
  await page.click('button:has-text("Listo")');
  await page.click('button:has-text("Salir")');
  await page.waitForURL("**/entrar");
  return admin;
}
