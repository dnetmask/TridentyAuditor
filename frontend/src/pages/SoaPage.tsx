import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useCompliance } from "../context/ComplianceContext";
import type { DirectoryUser, DocumentDetail, ImplementationStatus, SoaEntry, SoaSummary } from "../api/types";

const STATUS_LABEL: Record<ImplementationStatus, string> = {
  not_started: "Sin iniciar",
  in_progress: "En progreso",
  implemented: "Implementado",
};

export function SoaPage() {
  const { session } = useAuth();
  const { refresh: refreshCompliance } = useCompliance();
  const token = session!.token;
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";
  const canInstantiate = session!.role === "tenant_admin";

  const [entries, setEntries] = useState<SoaEntry[] | null>(null);
  const [summary, setSummary] = useState<SoaSummary | null>(null);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [openDomain, setOpenDomain] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [entriesData, summaryData] = await Promise.all([api.soaEntries(token), api.soaSummary(token)]);
    setEntries(entriesData);
    setSummary(summaryData);
  }

  useEffect(() => {
    reload();
    api.directory(token).then(setDirectory).catch(() => {});
    api.listDocuments(token).then(setDocuments).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const approvedDocuments = useMemo(
    () => documents.filter((d) => d.versions.some((v) => v.status === "approved")),
    [documents],
  );

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

  const byDomain = useMemo(() => {
    const groups = new Map<string, { name: string; entries: SoaEntry[] }>();
    for (const entry of entries ?? []) {
      const key = entry.control.domain.code;
      if (!groups.has(key)) groups.set(key, { name: entry.control.domain.name, entries: [] });
      groups.get(key)!.entries.push(entry);
    }
    return Array.from(groups.entries()).map(([code, v]) => ({ code, ...v }));
  }, [entries]);

  const started = entries !== null && entries.length > 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Declaración de Aplicabilidad (SoA)</h1>
          <p>
            MOD·SOA — los 93 controles del Anexo A con su aplicabilidad, justificación de
            exclusión, estado de implementación y dueño. Datos estructurados, no un PDF.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      {summary && started && (
        <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <SummaryStat label="Controles" value={summary.total} />
          <SummaryStat label="Aplicables" value={summary.applicable} />
          <SummaryStat label="Excluidos" value={summary.excluded} />
          <SummaryStat label="Implementados" value={summary.implemented} />
          <SummaryStat label="En progreso" value={summary.in_progress} />
          <SummaryStat label="Sin iniciar" value={summary.not_started} />
        </div>
      )}

      {entries === null ? (
        <div className="card empty-state">Cargando…</div>
      ) : !started ? (
        <div className="card empty-state">
          <p>Este tenant todavía no tiene una Declaración de Aplicabilidad.</p>
          {canInstantiate ? (
            <button className="btn btn-primary" disabled={busy} onClick={() => run(() => api.soaInstantiate(token))}>
              Comenzar SoA sobre ISO/IEC 27001:2022
            </button>
          ) : (
            <p className="muted">Pídele al Admin del tenant que la inicie.</p>
          )}
        </div>
      ) : (
        byDomain.map((domain) => (
          <div className="card domain-block" key={domain.code}>
            <div className="domain-header" onClick={() => setOpenDomain(openDomain === domain.code ? null : domain.code)}>
              <span className="domain-code">{domain.code}</span>
              <strong>{domain.name}</strong>
              <span className="domain-count">
                {domain.entries.filter((e) => e.is_applicable).length}/{domain.entries.length} aplicables{" "}
                {openDomain === domain.code ? "▲" : "▼"}
              </span>
            </div>
            {openDomain === domain.code && (
              <div className="control-list">
                {domain.entries.map((entry) => (
                  <SoaRow
                    key={entry.id}
                    entry={entry}
                    directory={directory}
                    approvedDocuments={approvedDocuments}
                    canWrite={canWrite}
                    busy={busy}
                    onUpdate={(payload) => run(() => api.soaUpdateEntry(token, entry.id, payload))}
                  />
                ))}
              </div>
            )}
          </div>
        ))
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

function SoaRow({
  entry,
  directory,
  approvedDocuments,
  canWrite,
  busy,
  onUpdate,
}: {
  entry: SoaEntry;
  directory: DirectoryUser[];
  approvedDocuments: DocumentDetail[];
  canWrite: boolean;
  busy: boolean;
  onUpdate: (payload: {
    is_applicable?: boolean;
    justification?: string | null;
    implementation_status?: ImplementationStatus;
    owner_user_id?: string | null;
    evidence_document_id?: string | null;
  }) => void;
}) {
  const [justification, setJustification] = useState(entry.justification ?? "");
  // La casilla se muestra de forma optimista: al desmarcar "Aplicable" no se envía
  // nada al backend todavía (requeriría justificación y sería rechazado con 422).
  // Solo se confirma la exclusión cuando la justificación se guarda al perder el foco.
  const [pendingExclude, setPendingExclude] = useState(!entry.is_applicable);
  const disabled = busy || !canWrite;

  useEffect(() => {
    setPendingExclude(!entry.is_applicable);
    setJustification(entry.justification ?? "");
  }, [entry.is_applicable, entry.justification]);

  function handleApplicableChange(checked: boolean) {
    if (checked) {
      setPendingExclude(false);
      onUpdate({ is_applicable: true });
    } else {
      setPendingExclude(true);
    }
  }

  function commitExclusion() {
    if (!justification.trim()) return;
    if (entry.is_applicable || justification !== (entry.justification ?? "")) {
      onUpdate({ is_applicable: false, justification });
    }
  }

  return (
    <div className="control-item" style={{ flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <span className="control-code">{entry.control.code}</span>
        <span style={{ flex: 1 }}>{entry.control.name}</span>
        <label style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.8rem" }}>
          <input
            type="checkbox"
            checked={!pendingExclude}
            disabled={disabled}
            onChange={(e) => handleApplicableChange(e.target.checked)}
          />
          Aplicable
        </label>
        <select
          value={entry.implementation_status}
          disabled={disabled || pendingExclude}
          onChange={(e) => onUpdate({ implementation_status: e.target.value as ImplementationStatus })}
        >
          {Object.entries(STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select
          value={entry.owner_user_id ?? ""}
          disabled={disabled}
          onChange={(e) => onUpdate({ owner_user_id: e.target.value || null })}
        >
          <option value="">— sin dueño —</option>
          {directory.map((u) => (
            <option key={u.id} value={u.id}>{u.full_name}</option>
          ))}
        </select>
      </div>
      {entry.control.evidence_guidance && (
        <div className="evidence-hint" style={{ paddingLeft: "5.5rem" }}>
          <strong>Evidencia sugerida:</strong> {entry.control.evidence_guidance}
        </div>
      )}
      {!pendingExclude && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", paddingLeft: "5.5rem" }}>
          <label style={{ fontSize: "0.8rem" }} htmlFor={`evidence-${entry.id}`}>Evidencia:</label>
          <select
            id={`evidence-${entry.id}`}
            value={entry.evidence_document_id ?? ""}
            disabled={disabled}
            onChange={(e) => onUpdate({ evidence_document_id: e.target.value || null })}
          >
            <option value="">— sin evidencia vinculada —</option>
            {approvedDocuments.map((d) => (
              <option key={d.id} value={d.id}>{d.code} · {d.title}</option>
            ))}
          </select>
        </div>
      )}
      {pendingExclude && (
        <div style={{ paddingLeft: "5.5rem" }}>
          <input
            type="text"
            placeholder="Justificación de exclusión (obligatoria)"
            value={justification}
            disabled={disabled}
            style={{ width: "100%", maxWidth: "32rem" }}
            onChange={(e) => setJustification(e.target.value)}
            onBlur={commitExclusion}
          />
          {entry.is_applicable && (
            <div className="muted" style={{ fontSize: "0.75rem", marginTop: "0.2rem" }}>
              Se excluirá al guardar la justificación.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
