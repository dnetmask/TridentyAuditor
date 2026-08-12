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

export interface DirectoryUser {
  id: string;
  full_name: string;
  role: UserRole;
}

// --- MOD·SOA ---

export type ImplementationStatus = "not_started" | "in_progress" | "implemented";

export interface DomainSummary {
  code: string;
  name: string;
}

export interface ControlSummary {
  id: string;
  code: string;
  name: string;
  domain: DomainSummary;
}

export interface SoaEntry {
  id: string;
  control: ControlSummary;
  is_applicable: boolean;
  justification: string | null;
  implementation_status: ImplementationStatus;
  owner_user_id: string | null;
  evidence_document_id: string | null;
  notes: string | null;
  updated_at: string;
}

export interface SoaSummary {
  total: number;
  applicable: number;
  excluded: number;
  implemented: number;
  in_progress: number;
  not_started: number;
}

// --- MOD·RSK ---

export type AssetCategory = "information" | "software" | "hardware" | "service" | "people" | "facility" | "other";
export type TreatmentDecision = "mitigate" | "accept" | "transfer" | "avoid";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RiskStatus = "open" | "treating" | "closed";

export interface Asset {
  id: string;
  name: string;
  description: string | null;
  category: AssetCategory;
  owner_user_id: string | null;
  created_at: string;
}

export interface Risk {
  id: string;
  asset_id: string | null;
  title: string;
  description: string | null;
  threat: string | null;
  vulnerability: string | null;
  likelihood: number;
  impact: number;
  inherent_score: number;
  inherent_level: RiskLevel;
  treatment_decision: TreatmentDecision | null;
  treatment_plan: string | null;
  residual_likelihood: number | null;
  residual_impact: number | null;
  residual_score: number | null;
  residual_level: RiskLevel | null;
  owner_user_id: string | null;
  status: RiskStatus;
  evidence_document_id: string | null;
  control_ids: string[];
  created_at: string;
  updated_at: string;
}
