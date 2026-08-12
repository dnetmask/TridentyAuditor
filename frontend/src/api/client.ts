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
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

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
  // --- autenticación ---
  login: (email: string, password: string) =>
    request<import("./types").LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  // --- Super Admin: tenants ---
  createTenant: (token: string, name: string, slug: string) =>
    request<import("./types").Tenant>("/api/v1/tenants", { method: "POST", token, body: { name, slug } }),

  listTenants: (token: string) => request<import("./types").Tenant[]>("/api/v1/tenants", { token }),

  // --- Usuarios (Super Admin: cualquier tenant · Admin del tenant: el propio) ---
  listUsers: (token: string) => request<import("./types").User[]>("/api/v1/auth/users", { token }),

  createUser: (
    token: string,
    payload: {
      email: string;
      password: string;
      full_name: string;
      role: import("./types").UserRole;
      tenant_id?: string | null;
    },
  ) => request<import("./types").User>("/api/v1/auth/users", { method: "POST", token, body: payload }),

  updateUser: (
    token: string,
    userId: string,
    payload: { full_name?: string; role?: import("./types").UserRole; is_active?: boolean; password?: string },
  ) => request<import("./types").User>(`/api/v1/auth/users/${userId}`, { method: "PATCH", token, body: payload }),

  directory: (token: string) => request<import("./types").DirectoryUser[]>("/api/v1/auth/directory", { token }),

  complianceOverview: (token: string) =>
    request<import("./types").ComplianceOverview>("/api/v1/compliance/overview", { token }),

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
      retention_months?: number | null;
      change_summary?: string | null;
    },
  ) => request<import("./types").DocumentDetail>("/api/v1/documents", { method: "POST", token, body: payload }),

  createVersion: (
    token: string,
    documentId: string,
    payload: { storage_ref: string; change_summary?: string | null },
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

  rejectVersion: (token: string, documentId: string, versionNumber: number) =>
    request<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions/${versionNumber}/reject`,
      { method: "POST", token },
    ),

  approveVersion: (token: string, documentId: string, versionNumber: number) =>
    request<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions/${versionNumber}/approve`,
      { method: "POST", token },
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

  // --- MOD·SOA (declaración de aplicabilidad) ---
  soaInstantiate: (token: string) =>
    request<{ created: number }>("/api/v1/soa/instantiate", { method: "POST", token }),

  soaEntries: (token: string) => request<import("./types").SoaEntry[]>("/api/v1/soa/entries", { token }),

  soaSummary: (token: string) => request<import("./types").SoaSummary>("/api/v1/soa/summary", { token }),

  soaUpdateEntry: (
    token: string,
    entryId: string,
    payload: {
      is_applicable?: boolean;
      justification?: string | null;
      implementation_status?: import("./types").ImplementationStatus;
      owner_user_id?: string | null;
      evidence_document_id?: string | null;
      notes?: string | null;
    },
  ) =>
    request<import("./types").SoaEntry>(`/api/v1/soa/entries/${entryId}`, {
      method: "PATCH",
      token,
      body: payload,
    }),

  // --- MOD·RSK (gestión de riesgos) ---
  listAssets: (token: string) => request<import("./types").Asset[]>("/api/v1/risk/assets", { token }),

  createAsset: (
    token: string,
    payload: { name: string; description?: string | null; category: import("./types").AssetCategory; owner_user_id?: string | null },
  ) => request<import("./types").Asset>("/api/v1/risk/assets", { method: "POST", token, body: payload }),

  listRisks: (token: string) => request<import("./types").Risk[]>("/api/v1/risk/risks", { token }),

  createRisk: (
    token: string,
    payload: {
      asset_id?: string | null;
      title: string;
      description?: string | null;
      threat?: string | null;
      vulnerability?: string | null;
      likelihood: number;
      impact: number;
      owner_user_id?: string | null;
      control_ids?: string[];
    },
  ) => request<import("./types").Risk>("/api/v1/risk/risks", { method: "POST", token, body: payload }),

  updateRisk: (
    token: string,
    riskId: string,
    payload: Partial<{
      asset_id: string | null;
      title: string;
      description: string | null;
      threat: string | null;
      vulnerability: string | null;
      likelihood: number;
      impact: number;
      treatment_decision: import("./types").TreatmentDecision;
      treatment_plan: string | null;
      residual_likelihood: number;
      residual_impact: number;
      owner_user_id: string | null;
      status: import("./types").RiskStatus;
      evidence_document_id: string | null;
      control_ids: string[];
    }>,
  ) => request<import("./types").Risk>(`/api/v1/risk/risks/${riskId}`, { method: "PATCH", token, body: payload }),
};
