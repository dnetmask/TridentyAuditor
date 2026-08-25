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

// Para multipart/form-data (subida de archivos) — sin fijar Content-Type a
// mano, el navegador agrega el boundary correcto solo si lo dejamos vacío.
async function requestFormData<T>(
  path: string,
  formData: FormData,
  token: string,
  method: "POST" = "POST",
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
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

  return (await res.json()) as T;
}

function filenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)"?/i.exec(header);
  return match ? decodeURIComponent(match[1]) : fallback;
}

// Descarga un binario protegido con Authorization: Bearer — no se puede usar
// un <a href> plano porque no lleva el token, así que se trae como blob y se
// dispara la descarga desde JS (ver DocumentsPage.tsx).
export async function downloadDocumentVersionFile(
  token: string,
  documentId: string,
  versionNumber: number,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/documents/${documentId}/versions/${versionNumber}/file`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
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
  const blob = await res.blob();
  const filename = filenameFromContentDisposition(
    res.headers.get("content-disposition"),
    `documento-v${versionNumber}`,
  );
  return { blob, filename };
}

export const api = {
  // --- autenticación ---
  login: (email: string, password: string) =>
    request<import("./types").LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  // --- Super Admin: tenants ---
  createTenant: (token: string, name: string, slug: string, frameworkId: string) =>
    request<import("./types").Tenant>("/api/v1/tenants", {
      method: "POST",
      token,
      body: { name, slug, framework_id: frameworkId },
    }),

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
  listFrameworks: () => request<import("./types").Framework[]>("/api/v1/frameworks"),

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
      file: File;
      retention_months?: number | null;
      change_summary?: string | null;
    },
  ) => {
    const form = new FormData();
    form.set("code", payload.code);
    form.set("title", payload.title);
    form.set("document_type", payload.document_type);
    if (payload.retention_months != null) form.set("retention_months", String(payload.retention_months));
    if (payload.change_summary) form.set("change_summary", payload.change_summary);
    form.set("file", payload.file);
    return requestFormData<import("./types").DocumentDetail>("/api/v1/documents", form, token);
  },

  createVersion: (token: string, documentId: string, payload: { file: File; change_summary?: string | null }) => {
    const form = new FormData();
    if (payload.change_summary) form.set("change_summary", payload.change_summary);
    form.set("file", payload.file);
    return requestFormData<import("./types").DocumentVersion>(
      `/api/v1/documents/${documentId}/versions`,
      form,
      token,
    );
  },

  downloadVersionFile: (token: string, documentId: string, versionNumber: number) =>
    downloadDocumentVersionFile(token, documentId, versionNumber),

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

  // --- MOD·AUD (auditoría interna) ---
  listAuditPrograms: (token: string) =>
    request<import("./types").AuditProgram[]>("/api/v1/audit/programs", { token }),

  createAuditProgram: (
    token: string,
    payload: {
      title: string;
      scope?: string | null;
      domain_id?: string | null;
      auditor_user_id?: string | null;
      planned_date?: string | null;
    },
  ) => request<import("./types").AuditProgram>("/api/v1/audit/programs", { method: "POST", token, body: payload }),

  updateAuditProgram: (
    token: string,
    programId: string,
    payload: Partial<{
      title: string;
      scope: string | null;
      domain_id: string | null;
      auditor_user_id: string | null;
      planned_date: string | null;
      executed_date: string | null;
      status: import("./types").AuditStatus;
    }>,
  ) =>
    request<import("./types").AuditProgram>(`/api/v1/audit/programs/${programId}`, {
      method: "PATCH",
      token,
      body: payload,
    }),

  listAuditFindings: (token: string, auditId?: string) =>
    request<import("./types").AuditFinding[]>(
      `/api/v1/audit/findings${auditId ? `?audit_id=${auditId}` : ""}`,
      { token },
    ),

  createAuditFinding: (
    token: string,
    payload: {
      audit_id: string;
      control_id?: string | null;
      classification: import("./types").FindingClassification;
      description: string;
      root_cause?: string | null;
      corrective_action?: string | null;
      owner_user_id?: string | null;
      due_date?: string | null;
    },
  ) => request<import("./types").AuditFinding>("/api/v1/audit/findings", { method: "POST", token, body: payload }),

  updateAuditFinding: (
    token: string,
    findingId: string,
    payload: Partial<{
      control_id: string | null;
      classification: import("./types").FindingClassification;
      description: string;
      root_cause: string | null;
      corrective_action: string | null;
      owner_user_id: string | null;
      due_date: string | null;
      status: import("./types").FindingStatus;
      evidence_document_id: string | null;
    }>,
  ) =>
    request<import("./types").AuditFinding>(`/api/v1/audit/findings/${findingId}`, {
      method: "PATCH",
      token,
      body: payload,
    }),

  auditSummary: (token: string) =>
    request<import("./types").AuditSummary>("/api/v1/audit/summary", { token }),
};
