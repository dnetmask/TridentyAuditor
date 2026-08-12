export type UserRole = "super_admin" | "tenant_admin" | "internal_auditor" | "viewer";

export type IsolationTier = "pooled" | "isolated";

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  isolation_tier: IsolationTier;
  created_at: string;
}

export type DocumentStatus = "draft" | "in_review" | "approved" | "obsolete";

export interface DocumentVersion {
  id: string;
  version_number: number;
  status: DocumentStatus;
  storage_ref: string;
  change_summary: string | null;
  created_by: string;
  approved_by: string | null;
  created_at: string;
  approved_at: string | null;
}

export interface DocumentDetail {
  id: string;
  code: string;
  title: string;
  document_type: string;
  control_id: string | null;
  retention_months: number | null;
  created_at: string;
  versions: DocumentVersion[];
}

export interface Requirement {
  id: string;
  code: string;
  text: string;
  order_index: number;
}

export interface Control {
  id: string;
  code: string;
  name: string;
  description: string | null;
  order_index: number;
  requirements: Requirement[];
}

export interface Domain {
  id: string;
  code: string;
  name: string;
  description: string | null;
  order_index: number;
  controls: Control[];
}

export interface FrameworkDetail {
  id: string;
  code: string;
  name: string;
  version: string;
  domains: Domain[];
}

export interface WizardPhase {
  id: string;
  number: number;
  code: string;
  name: string;
  objective: string;
}

export type WizardTaskStatus = "pending" | "done";

export interface WizardTask {
  id: string;
  phase_id: string;
  template_id: string | null;
  title: string;
  description: string | null;
  requires_evidence: boolean;
  owner: string | null;
  due_date: string | null;
  status: WizardTaskStatus;
  evidence_document_id: string | null;
  completed_at: string | null;
  created_at: string;
}

export type PhaseStatus = "locked" | "current" | "complete";

export interface PhaseProgress {
  phase: WizardPhase;
  status: PhaseStatus;
  tasks: WizardTask[];
  done_count: number;
  total_count: number;
}

export interface LoginResponse {
  access_token: string;
  user_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string | null;
  tenant_name: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string | null;
  is_active: boolean;
  created_at: string;
}
