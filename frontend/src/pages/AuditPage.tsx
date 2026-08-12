import { Fragment, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useCompliance } from "../context/ComplianceContext";
import { FindingClassificationBadge } from "../components/FindingClassificationBadge";
import type {
  AuditFinding,
  AuditProgram,
  AuditStatus,
  AuditSummary,
  DirectoryUser,
  DocumentDetail,
  FindingClassification,
  FindingStatus,
} from "../api/types";

const PROGRAM_STATUS_LABEL: Record<AuditStatus, string> = {
  planned: "Planeada",
  in_progress: "En curso",
  completed: "Completada",
};

const FINDING_STATUS_LABEL: Record<FindingStatus, string> = {
  open: "Abierto",
  in_progress: "En tratamiento",
  closed: "Cerrado",
};

const CLASSIFICATION_LABEL: Record<FindingClassification, string> = {
  major_nc: "No conformidad mayor",
  minor_nc: "No conformidad menor",
  observation: "Observación",
  improvement: "Oportunidad de mejora",
};

interface DomainOption {
  id: string;
  code: string;
  name: string;
}

interface ControlOption {
  id: string;
  code: string;
  name: string;
}

export function AuditPage() {
  const { session } = useAuth();
  const { refresh: refreshCompliance } = useCompliance();
  const token = session!.token;
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";

  const [programs, setPrograms] = useState<AuditProgram[] | null>(null);
  const [findings, setFindings] = useState<AuditFinding[] | null>(null);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [domains, setDomains] = useState<DomainOption[]>([]);
  const [controls, setControls] = useState<ControlOption[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreateProgram, setShowCreateProgram] = useState(false);
  const [showCreateFinding, setShowCreateFinding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [programsData, findingsData, summaryData] = await Promise.all([
      api.listAuditPrograms(token),
      api.listAuditFindings(token),
      api.auditSummary(token),
    ]);
    setPrograms(programsData);
    setFindings(findingsData);
    setSummary(summaryData);
  }

  useEffect(() => {
    reload();
    api.directory(token).then(setDirectory).catch(() => {});
    api.listDocuments(token).then(setDocuments).catch(() => {});
    api
      .getFramework("ISO27001:2022")
      .then((fw) => {
        setDomains(fw.domains.map((d) => ({ id: d.id, code: d.code, name: d.name })));
        setControls(fw.domains.flatMap((d) => d.controls.map((c) => ({ id: c.id, code: c.code, name: c.name }))));
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
      refreshCompliance();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  const approvedDocuments = useMemo(
    () => documents.filter((d) => d.versions.some((v) => v.status === "approved")),
    [documents],
  );
  const programTitle = (id: string) => programs?.find((p) => p.id === id)?.title ?? "—";

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Auditoría interna</h1>
          <p>
            MOD·AUD — programa anual de auditoría, hallazgos clasificados y su CAPA
            (causa raíz, acción correctiva, responsable y evidencia de cierre).
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      {summary && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <SummaryStat label="Auditorías" value={summary.total_programs} />
          <SummaryStat label="Hallazgos" value={summary.total_findings} />
          <SummaryStat label="Abiertos" value={summary.open_findings} />
          <SummaryStat label="En tratamiento" value={summary.in_progress_findings} />
          <SummaryStat label="Cerrados" value={summary.closed_findings} />
          <SummaryStat label="No conf. mayores" value={summary.major_nc} />
          <SummaryStat label="No conf. menores" value={summary.minor_nc} />
        </div>
      )}

      <div className="page-header" style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Programa de auditoría</h2>
        {canWrite && (
          <button className="btn btn-secondary btn-sm" onClick={() => setShowCreateProgram(true)}>
            + Nueva auditoría
          </button>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        {programs === null ? (
          <div className="empty-state">Cargando…</div>
        ) : programs.length === 0 ? (
          <div className="empty-state">Sin auditorías planeadas todavía.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Título</th>
                <th>Dominio</th>
                <th>Auditor</th>
                <th>Fecha planeada</th>
                <th>Fecha ejecutada</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {programs.map((p) => (
                <ProgramRow
                  key={p.id}
                  program={p}
                  directory={directory}
                  canWrite={canWrite}
                  busy={busy}
                  onUpdate={(payload) => run(() => api.updateAuditProgram(token, p.id, payload))}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="page-header" style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Hallazgos</h2>
        {canWrite && programs && programs.length > 0 && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreateFinding(true)}>
            + Nuevo hallazgo
          </button>
        )}
      </div>

      <div className="card">
        {findings === null ? (
          <div className="empty-state">Cargando…</div>
        ) : findings.length === 0 ? (
          <div className="empty-state">Sin hallazgos registrados todavía.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Hallazgo</th>
                <th>Auditoría</th>
                <th>Control</th>
                <th>Clasificación</th>
                <th>Vencimiento</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => {
                const isOpen = expandedId === f.id;
                return (
                  <Fragment key={f.id}>
                    <tr className="clickable" onClick={() => setExpandedId(isOpen ? null : f.id)}>
                      <td>{f.description}</td>
                      <td>{programTitle(f.audit_id)}</td>
                      <td>{f.control ? `${f.control.code}` : "—"}</td>
                      <td><FindingClassificationBadge classification={f.classification} /></td>
                      <td>{f.due_date ?? "—"}</td>
                      <td>{FINDING_STATUS_LABEL[f.status]}</td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={6} style={{ padding: 0 }}>
                          <FindingDetailPanel
                            finding={f}
                            directory={directory}
                            documents={approvedDocuments}
                            canWrite={canWrite}
                            busy={busy}
                            onUpdate={(payload) => run(() => api.updateAuditFinding(token, f.id, payload))}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreateProgram && (
        <CreateProgramModal
          token={token}
          domains={domains}
          directory={directory}
          onClose={() => setShowCreateProgram(false)}
          onCreated={async () => {
            setShowCreateProgram(false);
            await reload();
          }}
        />
      )}

      {showCreateFinding && (
        <CreateFindingModal
          token={token}
          programs={programs ?? []}
          controls={controls}
          onClose={() => setShowCreateFinding(false)}
          onCreated={async () => {
            setShowCreateFinding(false);
            await reload();
            refreshCompliance();
          }}
        />
      )}
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{value}</div>
      <div className="muted" style={{ fontSize: "0.78rem" }}>{label}</div>
    </div>
  );
}

function ProgramRow({
  program,
  directory,
  canWrite,
  busy,
  onUpdate,
}: {
  program: AuditProgram;
  directory: DirectoryUser[];
  canWrite: boolean;
  busy: boolean;
  onUpdate: (payload: { status?: AuditStatus; executed_date?: string | null }) => void;
}) {
  const [executedDate, setExecutedDate] = useState(program.executed_date ?? "");
  const disabled = busy || !canWrite;

  return (
    <tr>
      <td>{program.title}</td>
      <td>{program.domain ? `${program.domain.code} · ${program.domain.name}` : "Todo el SGSI"}</td>
      <td>{directory.find((u) => u.id === program.auditor_user_id)?.full_name ?? "—"}</td>
      <td>{program.planned_date ?? "—"}</td>
      <td>
        <input
          type="date"
          value={executedDate}
          disabled={disabled}
          onChange={(e) => setExecutedDate(e.target.value)}
          onBlur={() => executedDate !== (program.executed_date ?? "") && onUpdate({ executed_date: executedDate || null })}
        />
      </td>
      <td>
        <select
          value={program.status}
          disabled={disabled}
          onChange={(e) => onUpdate({ status: e.target.value as AuditStatus })}
        >
          {Object.entries(PROGRAM_STATUS_LABEL).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </td>
    </tr>
  );
}

function FindingDetailPanel({
  finding,
  directory,
  documents,
  canWrite,
  busy,
  onUpdate,
}: {
  finding: AuditFinding;
  directory: DirectoryUser[];
  documents: DocumentDetail[];
  canWrite: boolean;
  busy: boolean;
  onUpdate: (payload: Record<string, unknown>) => void;
}) {
  const [rootCause, setRootCause] = useState(finding.root_cause ?? "");
  const [correctiveAction, setCorrectiveAction] = useState(finding.corrective_action ?? "");
  const disabled = busy || !canWrite;

  return (
    <div className="risk-detail-panel">
      <div className="risk-detail-grid">
        <div className="field">
          <label>Responsable</label>
          <select
            value={finding.owner_user_id ?? ""}
            disabled={disabled}
            onChange={(e) => onUpdate({ owner_user_id: e.target.value || null })}
          >
            <option value="">— sin dueño —</option>
            {directory.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Fecha de vencimiento</label>
          <input
            type="date"
            defaultValue={finding.due_date ?? ""}
            disabled={disabled}
            onBlur={(e) => e.target.value !== (finding.due_date ?? "") && onUpdate({ due_date: e.target.value || null })}
          />
        </div>
        <div className="field">
          <label>Estado</label>
          <select
            value={finding.status}
            disabled={disabled}
            onChange={(e) => onUpdate({ status: e.target.value })}
          >
            {Object.entries(FINDING_STATUS_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Evidencia de cierre</label>
          <select
            value={finding.evidence_document_id ?? ""}
            disabled={disabled}
            onChange={(e) => onUpdate({ evidence_document_id: e.target.value || null })}
          >
            <option value="">— sin evidencia —</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.code} · {d.title}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <label>Causa raíz</label>
        <textarea
          rows={2}
          value={rootCause}
          disabled={disabled}
          onChange={(e) => setRootCause(e.target.value)}
          onBlur={() => rootCause !== (finding.root_cause ?? "") && onUpdate({ root_cause: rootCause })}
        />
      </div>

      <div className="field">
        <label>Acción correctiva</label>
        <textarea
          rows={2}
          value={correctiveAction}
          disabled={disabled}
          onChange={(e) => setCorrectiveAction(e.target.value)}
          onBlur={() => correctiveAction !== (finding.corrective_action ?? "") && onUpdate({ corrective_action: correctiveAction })}
        />
        <div className="evidence-hint" style={{ marginTop: "0.3rem" }}>
          <strong>Evidencia sugerida:</strong> algo que demuestre que la acción correctiva se
          ejecutó — captura de la configuración corregida, procedimiento actualizado y
          publicado, registro de la capacitación de refuerzo. La plataforma no deja marcar
          el hallazgo como <strong>Cerrado</strong> sin un documento de evidencia con una
          versión aprobada.
        </div>
      </div>
    </div>
  );
}

function CreateProgramModal({
  token,
  domains,
  directory,
  onClose,
  onCreated,
}: {
  token: string;
  domains: DomainOption[];
  directory: DirectoryUser[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState("");
  const [domainId, setDomainId] = useState("");
  const [auditorUserId, setAuditorUserId] = useState("");
  const [plannedDate, setPlannedDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createAuditProgram(token, {
        title,
        scope: scope || null,
        domain_id: domainId || null,
        auditor_user_id: auditorUserId || null,
        planned_date: plannedDate || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la auditoría");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nueva auditoría</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="au-title">Título</label>
            <input id="au-title" required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Auditoría interna A.5 — Q1 2026" />
          </div>
          <div className="field">
            <label htmlFor="au-scope">Alcance</label>
            <textarea id="au-scope" rows={2} value={scope} onChange={(e) => setScope(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="au-domain">Dominio (opcional)</label>
            <select id="au-domain" value={domainId} onChange={(e) => setDomainId(e.target.value)}>
              <option value="">— todo el SGSI —</option>
              {domains.map((d) => (
                <option key={d.id} value={d.id}>{d.code} · {d.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="au-auditor">Auditor</label>
            <select id="au-auditor" value={auditorUserId} onChange={(e) => setAuditorUserId(e.target.value)}>
              <option value="">— sin asignar —</option>
              {directory.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="au-planned">Fecha planeada</label>
            <input id="au-planned" type="date" value={plannedDate} onChange={(e) => setPlannedDate(e.target.value)} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Creando…" : "Crear"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CreateFindingModal({
  token,
  programs,
  controls,
  onClose,
  onCreated,
}: {
  token: string;
  programs: AuditProgram[];
  controls: ControlOption[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [auditId, setAuditId] = useState(programs[0]?.id ?? "");
  const [controlId, setControlId] = useState("");
  const [classification, setClassification] = useState<FindingClassification>("minor_nc");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createAuditFinding(token, {
        audit_id: auditId,
        control_id: controlId || null,
        classification,
        description,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el hallazgo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo hallazgo</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="f-audit">Auditoría</label>
            <select id="f-audit" required value={auditId} onChange={(e) => setAuditId(e.target.value)}>
              {programs.map((p) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-control">Control relacionado (opcional)</label>
            <select id="f-control" value={controlId} onChange={(e) => setControlId(e.target.value)}>
              <option value="">— sin control específico —</option>
              {controls.map((c) => (
                <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-classification">Clasificación</label>
            <select
              id="f-classification"
              value={classification}
              onChange={(e) => setClassification(e.target.value as FindingClassification)}
            >
              {Object.entries(CLASSIFICATION_LABEL).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-description">Descripción</label>
            <textarea id="f-description" required rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Creando…" : "Crear"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
