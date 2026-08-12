const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  token?: string | null;
  adminToken?: string | null;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.adminToken) headers["X-Admin-Token"] = options.adminToken;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // --- dev-only auth stand-in (Fase 2 lo reemplaza por Keycloak/OIDC) ---
  mintDevToken: (tenantId: string, sub: string, role: string) =>
    request<{ access_token: string }>("/api/v1/dev/token", {
      method: "POST",
      body: { tenant_id: tenantId, sub, role },
    }),

  createTenant: (adminToken: string, name: string, slug: string) =>
    request<import("./types").Tenant>("/api/v1/tenants", {
      method: "POST",
      adminToken,
      body: { name, slug },
    }),

  // --- motor de frameworks ---
  getFramework: (code: string) =>
    request<import("./types").FrameworkDetail>(`/api/v1/frameworks/${encodeURIComponent(code)}`),

  // --- MOD·DOC ---
  listDocuments: (token: string) =>
    request<import("./types").DocumentDetail[]>("/api/v1/documents", { token }),

  createDocument: (
    token: string,
    payload: {
      code: string;
      title: string;
      document_type: string;
      storage_ref: string;
      created_by: string;
      retention_months?: number | null;
      change_summary?: string | null;
    },
  ) => request<import("./types").DocumentDetail>("/api/v1/documents", { method: "POST", token, body: payload }),

  createVersion: (
    token: string,
    documentId: string,
    payload: { storage_ref: string; created_by: string; change_summary?: string | null },
  ) =>
    request<import("./types").DocumentVersion>(`/api/v1/documents/${documentId}/versions`, {
      method: "POST",
      token,
      body: payload,
    }),

  submitForReview: (token: string, documentId: string, versionNumber: number) =>
    request<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions/${versionNumber}/submit`,
      { method: "POST", token },
    ),

  rejectVersion: (token: string, documentId: string, versionNumber: number, actor: string) =>
    request<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions/${versionNumber}/reject`,
      { method: "POST", token, body: { actor } },
    ),

  approveVersion: (token: string, documentId: string, versionNumber: number, actor: string) =>
    request<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions/${versionNumber}/approve`,
      { method: "POST", token, body: { actor } },
    ),

  // --- MOD·WZD (asistente paso a paso) ---
  wizardInstantiate: (token: string) =>
    request<{ created: number }>("/api/v1/wizard/instantiate", { method: "POST", token }),

  wizardProgress: (token: string) =>
    request<import("./types").PhaseProgress[]>("/api/v1/wizard/progress", { token }),

  wizardCreateTask: (
    token: string,
    payload: {
      phase_id: string;
      title: string;
      description?: string | null;
      requires_evidence: boolean;
      owner?: string | null;
      due_date?: string | null;
    },
  ) => request<import("./types").WizardTask>("/api/v1/wizard/tasks", { method: "POST", token, body: payload }),

  wizardUpdateTask: (
    token: string,
    taskId: string,
    payload: { owner?: string | null; due_date?: string | null; evidence_document_id?: string | null },
  ) =>
    request<import("./types").WizardTask>(`/api/v1/wizard/tasks/${taskId}`, {
      method: "PATCH",
      token,
      body: payload,
    }),

  wizardCompleteTask: (token: string, taskId: string) =>
    request<import("./types").WizardTask>(`/api/v1/wizard/tasks/${taskId}/complete`, {
      method: "POST",
      token,
    }),

  wizardReopenTask: (token: string, taskId: string) =>
    request<import("./types").WizardTask>(`/api/v1/wizard/tasks/${taskId}/reopen`, {
      method: "POST",
      token,
    }),
};
