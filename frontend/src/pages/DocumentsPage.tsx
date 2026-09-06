import { Fragment, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useCompliance } from "../context/ComplianceContext";
import { StatusBadge } from "../components/StatusBadge";
import { DocumentViewer } from "../components/DocumentViewer";
import { DocumentLifecyclePanel } from "../components/DocumentLifecyclePanel";
import type {
  Acknowledgment,
  ApprovalStep,
  Area,
  DirectoryUser,
  DocumentControl,
  DocumentDetail,
  DocumentOrigin,
  DocumentVersion,
} from "../api/types";

function formatFileSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const DOCUMENT_TYPES = [
  { value: "policy", label: "Política" },
  { value: "procedure", label: "Procedimiento" },
  { value: "record", label: "Registro" },
  { value: "other", label: "Otro" },
];

const DOCUMENT_TYPE_HINT: Record<string, string> = {
  policy: "Documento aprobado por la dirección que fija intenciones y reglas generales (ej. Política de Seguridad de la Información).",
  procedure: "Pasos operativos detallados para ejecutar una actividad de forma consistente (ej. gestión de cambios, copias de respaldo).",
  record: "Evidencia de que algo ocurrió: logs, actas, capturas de pantalla, formularios firmados, reportes de una herramienta.",
  other: "Cualquier otro documento de soporte del SGSI (diagramas, contratos, certificados).",
};

// Días de hoy a la fecha (negativo = ya venció) — "días para revisión" se
// calcula en vivo, nunca se guarda un contador que se desactualiza solo.
function daysUntil(isoDate: string): number {
  const target = new Date(`${isoDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

function ReviewCell({ doc }: { doc: DocumentDetail }) {
  if (doc.retired_at) return <span className="muted">—</span>;
  if (!doc.next_review_date) return <span className="muted">sin programar</span>;
  const days = daysUntil(doc.next_review_date);
  if (days < 0) return <span className="review-overdue">vencida hace {-days} d</span>;
  if (days <= 30) return <span className="review-soon">en {days} d</span>;
  return (
    <span className="review-ok" title={doc.next_review_date}>
      faltan {days} d
    </span>
  );
}

const STEP_LABELS: Record<string, string> = {
  area_manager: "Gerente de área",
  security: "Seguridad de la información",
};

export function DocumentsPage() {
  const { session } = useAuth();
  const { refresh: refreshCompliance } = useCompliance();
  const token = session!.token;
  const userId = session!.userId;
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";
  const canReview = session!.role === "tenant_admin";

  const [documents, setDocuments] = useState<DocumentDetail[] | null>(null);
  const [areas, setAreas] = useState<Area[]>([]);
  const [controls, setControls] = useState<DocumentControl[]>([]);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [myPending, setMyPending] = useState<Acknowledgment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showAreas, setShowAreas] = useState(false);
  const [editDoc, setEditDoc] = useState<DocumentDetail | null>(null);
  const [reason, setReason] = useState<
    | { kind: "reject"; docId: string; versionNumber: number }
    | { kind: "retire"; docId: string; docCode: string }
    | null
  >(null);
  const [busy, setBusy] = useState(false);

  // Filtros — todo en el cliente, sobre la lista que ya se carga hoy.
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterArea, setFilterArea] = useState("");
  const [filterVigencia, setFilterVigencia] = useState<"vigentes" | "derogados" | "todos">("vigentes");

  async function reload() {
    try {
      setDocuments(await api.listDocuments(token));
      api.listAreas(token).then(setAreas).catch(() => {});
      api.myAcknowledgments(token).then(setMyPending).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de documentos");
    }
  }

  useEffect(() => {
    reload();
    api.listAreas(token).then(setAreas).catch(() => {});
    api.directory(token).then(setDirectory).catch(() => {});
    if (session!.frameworkCode) {
      api
        .getFramework(session!.frameworkCode)
        .then((fw) =>
          setControls(fw.domains.flatMap((d) => d.controls.map((c) => ({ id: c.id, code: c.code, name: c.name })))),
        )
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runAction(action: () => Promise<unknown>) {
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

  async function handleDownload(documentId: string, versionNumber: number) {
    setError(null);
    try {
      const { blob, filename } = await api.downloadVersionFile(token, documentId, versionNumber);
      triggerBrowserDownload(blob, filename);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar el archivo");
    }
  }

  // Botón Ver: previsualización embebida (visor en modal) sin salir de la app.
  const [viewing, setViewing] = useState<{ documentId: string; version: number; title: string } | null>(null);

  const filtered = useMemo(() => {
    if (documents === null) return null;
    const text = search.trim().toLowerCase();
    return documents.filter((doc) => {
      if (filterVigencia === "vigentes" && doc.retired_at) return false;
      if (filterVigencia === "derogados" && !doc.retired_at) return false;
      if (filterType && doc.document_type !== filterType) return false;
      if (filterArea && doc.area?.id !== filterArea) return false;
      if (filterStatus) {
        const current = currentVersion(doc);
        if (!current || current.status !== filterStatus) return false;
      }
      if (text && !doc.code.toLowerCase().includes(text) && !doc.title.toLowerCase().includes(text)) {
        return false;
      }
      return true;
    });
  }, [documents, search, filterType, filterStatus, filterArea, filterVigencia]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Control documental</h1>
          <p>
            MOD·DOC — versionado y aprobación multinivel: firma el gerente del área
            encargada y luego seguridad de la información. Solo puede haber una copia
            vigente (<code>approved</code>) por documento; aprobar una versión nueva
            vuelve obsoleta a la anterior.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {canReview && (
            <button className="btn btn-secondary" onClick={() => setShowAreas(true)}>
              Áreas
            </button>
          )}
          {canWrite && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + Nuevo documento
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      {myPending.length > 0 && (
        <div className="alert alert-warning pending-banner" style={{ marginBottom: "1rem" }}>
          <strong>Tienes {myPending.length} documento{myPending.length === 1 ? "" : "s"} obligatorio{myPending.length === 1 ? "" : "s"} sin leer.</strong>
          <div className="pending-list">
            {myPending.map((ack) => {
              const d = documents?.find((doc) => doc.id === ack.document_id);
              return (
                <div key={ack.id} className="pending-item">
                  <span>{d ? `${d.code} · ${d.title}` : "Documento"}</span>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={busy}
                    onClick={() => runAction(() => api.acknowledgeDocument(token, ack.document_id))}
                  >
                    Marcar leído y entendido
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="card">
        <div className="filter-bar">
          <input
            type="search"
            placeholder="Buscar código o título…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} aria-label="Filtrar por tipo">
            <option value="">Todos los tipos</option>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} aria-label="Filtrar por estado">
            <option value="">Todos los estados</option>
            <option value="draft">Borrador</option>
            <option value="in_review">En revisión</option>
            <option value="approved">Aprobado</option>
            <option value="obsolete">Obsoleto</option>
          </select>
          <select value={filterArea} onChange={(e) => setFilterArea(e.target.value)} aria-label="Filtrar por área">
            <option value="">Todas las áreas</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <select
            value={filterVigencia}
            onChange={(e) => setFilterVigencia(e.target.value as typeof filterVigencia)}
            aria-label="Filtrar por vigencia"
          >
            <option value="vigentes">Vigentes</option>
            <option value="derogados">Derogados</option>
            <option value="todos">Todos</option>
          </select>
        </div>

        {filtered === null ? (
          <div className="empty-state">Cargando…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            {documents && documents.length > 0
              ? "Ningún documento coincide con los filtros."
              : "Todavía no hay documentos en este tenant."}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Título</th>
                <th>Tipo</th>
                <th>Área</th>
                <th>Próx. revisión</th>
                <th>Versión vigente</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => {
                const current = currentVersion(doc);
                const isOpen = expandedId === doc.id;
                return (
                  <Fragment key={doc.id}>
                    <tr className="clickable" onClick={() => setExpandedId(isOpen ? null : doc.id)}>
                      <td><code>{doc.code}</code></td>
                      <td>{doc.title}</td>
                      <td>{DOCUMENT_TYPES.find((t) => t.value === doc.document_type)?.label ?? doc.document_type}</td>
                      <td>{doc.area?.name ?? <span className="muted">—</span>}</td>
                      <td><ReviewCell doc={doc} /></td>
                      <td>
                        {doc.retired_at ? (
                          <span className="retired-badge" title={doc.retirement_reason ?? undefined}>Derogado</span>
                        ) : current ? (
                          <>
                            v{current.version_number} <StatusBadge status={current.status} />
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={6} style={{ padding: 0 }}>
                          <DocumentDetailPanel
                            doc={doc}
                            token={token}
                            userId={userId}
                            directory={directory}
                            canWrite={canWrite}
                            canReview={canReview}
                            busy={busy}
                            onAction={runAction}
                            onChanged={reload}
                            onDownload={handleDownload}
                            onView={(versionNumber) =>
                              setViewing({
                                documentId: doc.id,
                                version: versionNumber,
                                title: `${doc.code} · ${doc.title}`,
                              })
                            }
                            onEdit={() => setEditDoc(doc)}
                            onRetire={() => setReason({ kind: "retire", docId: doc.id, docCode: doc.code })}
                            onReject={(versionNumber) =>
                              setReason({ kind: "reject", docId: doc.id, versionNumber })
                            }
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

      {showCreate && (
        <DocumentFormModal
          token={token}
          areas={areas}
          controls={controls}
          onClose={() => setShowCreate(false)}
          onSaved={async () => {
            setShowCreate(false);
            await reload();
          }}
        />
      )}

      {editDoc && (
        <DocumentFormModal
          token={token}
          areas={areas}
          controls={controls}
          existing={editDoc}
          onClose={() => setEditDoc(null)}
          onSaved={async () => {
            setEditDoc(null);
            await reload();
          }}
        />
      )}

      {showAreas && (
        <AreasModal
          token={token}
          areas={areas}
          onChanged={() => api.listAreas(token).then(setAreas).catch(() => {})}
          onClose={() => setShowAreas(false)}
        />
      )}

      {reason && (
        <ReasonModal
          title={reason.kind === "reject" ? "Rechazar versión" : `Derogar ${reason.kind === "retire" ? reason.docCode : ""}`}
          label={
            reason.kind === "reject"
              ? "Motivo del rechazo (queda registrado en la versión)"
              : "Motivo de la derogación (el documento deja de contar como evidencia)"
          }
          confirmLabel={reason.kind === "reject" ? "Rechazar" : "Derogar"}
          danger
          onClose={() => setReason(null)}
          onConfirm={async (text) => {
            const current = reason;
            setReason(null);
            await runAction(() =>
              current.kind === "reject"
                ? api.rejectVersion(token, current.docId, current.versionNumber, text)
                : api.retireDocument(token, current.docId, text),
            );
          }}
        />
      )}

      {viewing && (
        <DocumentViewer
          token={token}
          documentId={viewing.documentId}
          versionNumber={viewing.version}
          title={viewing.title}
          onClose={() => setViewing(null)}
        />
      )}
    </div>
  );
}

function currentVersion(doc: DocumentDetail) {
  return [...doc.versions].sort((a, b) => b.version_number - a.version_number)[0] ?? null;
}

// Aprobación multinivel (Fase 2): con área firma primero su gerente (o un
// Admin en su lugar) y siempre cierra seguridad de la información (Admin).
function requiredSteps(doc: DocumentDetail): ApprovalStep[] {
  return doc.area ? ["area_manager", "security"] : ["security"];
}

function nextPendingStep(doc: DocumentDetail, version: DocumentVersion): ApprovalStep | null {
  const signed = new Set(version.approvals.map((a) => a.step));
  return requiredSteps(doc).find((step) => !signed.has(step)) ?? null;
}

// El navegador puede mostrar estos tipos directo (botón Ver); Office se
// descarga siempre.
function isViewable(contentType: string | null): boolean {
  if (!contentType) return false;
  return (
    contentType === "application/pdf" ||
    contentType.startsWith("image/") ||
    contentType.startsWith("text/")
  );
}

// Panel de copia controlada: los tres nombres que el auditor pide ver.
// Elaboró = quien subió la versión; Revisó = firma del gerente de área
// (Fase 2); Aprobó = firma de seguridad de la información (o el approved_by
// de un solo paso en versiones anteriores a la Fase 2).
function CopyControlLine({ version }: { version: DocumentVersion }) {
  if (version.status !== "approved" && version.status !== "obsolete") return null;
  const reviewed = version.approvals.find((a) => a.step === "area_manager");
  const approved = version.approvals.find((a) => a.step === "security");
  const fmt = (iso: string) => new Date(iso).toLocaleDateString();
  return (
    <span className="copy-control">
      <span>
        <strong>Elaboró:</strong> {version.created_by} · {fmt(version.created_at)}
      </span>
      <span>
        <strong>Revisó:</strong>{" "}
        {reviewed ? `${reviewed.signed_by} · ${fmt(reviewed.signed_at)}` : "—"}
      </span>
      <span>
        <strong>Aprobó:</strong>{" "}
        {approved
          ? `${approved.signed_by} · ${fmt(approved.signed_at)}`
          : version.approved_by
            ? `${version.approved_by}${version.approved_at ? ` · ${fmt(version.approved_at)}` : ""}`
            : "—"}
      </span>
    </span>
  );
}

function ApprovalSteps({ doc, version }: { doc: DocumentDetail; version: DocumentVersion }) {
  // El checklist aplica mientras se firma; una vez aprobada, la línea de
  // copia controlada (Elaboró/Revisó/Aprobó) toma su lugar.
  if (version.status !== "in_review") return null;
  const signedByStep = new Map(version.approvals.map((a) => [a.step, a]));
  return (
    <span className="approval-steps">
      {requiredSteps(doc).map((step) => {
        const signature = signedByStep.get(step);
        return (
          <span key={step} className={signature ? "approval-step approval-step-done" : "approval-step"}>
            {signature ? "✓" : "○"} {STEP_LABELS[step]}
            {step === "area_manager" && doc.area ? ` (${doc.area.name})` : ""}
            {signature
              ? `: ${signature.signed_by} · ${new Date(signature.signed_at).toLocaleDateString()}`
              : ": pendiente"}
          </span>
        );
      })}
    </span>
  );
}

function DocumentDetailPanel({
  doc,
  token,
  userId,
  directory,
  canWrite,
  canReview,
  busy,
  onAction,
  onChanged,
  onDownload,
  onView,
  onEdit,
  onRetire,
  onReject,
}: {
  doc: DocumentDetail;
  token: string;
  userId: string;
  directory: DirectoryUser[];
  canWrite: boolean;
  canReview: boolean;
  busy: boolean;
  onAction: (action: () => Promise<unknown>) => Promise<void>;
  onChanged: () => void;
  onDownload: (documentId: string, versionNumber: number) => void;
  onView: (versionNumber: number) => void;
  onEdit: () => void;
  onRetire: () => void;
  onReject: (versionNumber: number) => void;
}) {
  const [showNewVersion, setShowNewVersion] = useState(false);
  const hasOpenVersion = doc.versions.some((v) => v.status === "draft" || v.status === "in_review");
  const sorted = [...doc.versions].sort((a, b) => b.version_number - a.version_number);
  const retired = doc.retired_at != null;

  return (
    <div className="doc-detail-panel">
      <div className="doc-meta-row">
        <span className="muted">
          {doc.origin === "external"
            ? `Origen externo${doc.external_source ? ` · ${doc.external_source}` : ""}`
            : "Origen interno"}
          {doc.implementation_date ? ` · implementado el ${doc.implementation_date}` : ""}
          {doc.review_frequency_months ? ` · revisión cada ${doc.review_frequency_months} meses` : ""}
          {doc.retention_months ? ` · retención ${doc.retention_months} meses` : ""}
        </span>
        {doc.controls.length > 0 && (
          <div className="control-chips" style={{ marginTop: "0.35rem" }}>
            {doc.controls.map((c) => (
              <span className="control-chip" key={c.id} title={c.name}>
                {c.code}
              </span>
            ))}
          </div>
        )}
        {retired && (
          <div className="alert alert-error" style={{ marginTop: "0.5rem" }}>
            Derogado por {doc.retired_by} — {doc.retirement_reason}
          </div>
        )}
        {!retired && (
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            {canWrite && (
              <button className="btn btn-secondary btn-sm" disabled={busy} onClick={onEdit}>
                Editar metadatos
              </button>
            )}
            {canReview && (
              <button className="btn btn-danger btn-sm" disabled={busy} onClick={onRetire}>
                Derogar
              </button>
            )}
          </div>
        )}
      </div>

      {sorted.map((v) => (
        <div className="version-row" key={v.id}>
          <div className="version-meta">
            <span>
              <strong>v{v.version_number}</strong> · <StatusBadge status={v.status} />
            </span>
            <span className="muted">
              {v.original_filename ?? "sin archivo"}
              {v.file_size != null ? ` (${formatFileSize(v.file_size)})` : ""}
              {v.file_sha256 ? ` · sha256 ` : ""}
              {v.file_sha256 && <code title={v.file_sha256}>{v.file_sha256.slice(0, 12)}…</code>}
            </span>
            {v.change_summary && <span className="muted">{v.change_summary}</span>}
            {v.rejection_reason && (
              <span className="review-overdue">
                Rechazada por {v.rejected_by}: {v.rejection_reason}
              </span>
            )}
            <CopyControlLine version={v} />
            <ApprovalSteps doc={doc} version={v} />
          </div>
          <div className="version-actions">
            {v.original_filename && isViewable(v.content_type) && (
              <button className="btn btn-secondary btn-sm" onClick={() => onView(v.version_number)}>
                Ver
              </button>
            )}
            {v.original_filename && (
              <button className="btn btn-secondary btn-sm" onClick={() => onDownload(doc.id, v.version_number)}>
                Descargar
              </button>
            )}
            {!retired && v.status === "draft" && canWrite && (
              <button
                className="btn btn-secondary btn-sm"
                disabled={busy}
                onClick={() => onAction(() => api.submitForReview(token, doc.id, v.version_number))}
              >
                Enviar a revisión
              </button>
            )}
            {!retired && v.status === "in_review" && (() => {
              const nextStep = nextPendingStep(doc, v);
              const isAreaManager = doc.area?.manager_user_id === userId;
              const canSign =
                nextStep != null &&
                (canReview || (nextStep === "area_manager" && isAreaManager));
              return (
                <>
                  {canSign && (
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={busy}
                      onClick={() => onAction(() => api.approveVersion(token, doc.id, v.version_number))}
                    >
                      {nextStep === "security" ? "Aprobar" : "Firmar como gerente de área"}
                    </button>
                  )}
                  {canReview && (
                    <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => onReject(v.version_number)}>
                      Rechazar
                    </button>
                  )}
                </>
              );
            })()}
          </div>
        </div>
      ))}

      {canWrite && !retired && (
        <div style={{ padding: "0.75rem 1rem" }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={busy || hasOpenVersion}
            title={hasOpenVersion ? "Ya hay una versión en borrador o revisión" : undefined}
            onClick={() => setShowNewVersion(true)}
          >
            + Nueva versión
          </button>
        </div>
      )}

      <DocumentLifecyclePanel
        token={token}
        doc={doc}
        canWrite={canWrite}
        canReview={canReview}
        directory={directory}
        onChanged={onChanged}
      />

      {showNewVersion && (
        <NewVersionModal
          token={token}
          documentId={doc.id}
          onClose={() => setShowNewVersion(false)}
          onCreated={async () => {
            setShowNewVersion(false);
            await onAction(async () => {});
          }}
        />
      )}
    </div>
  );
}

function ControlPicker({
  controls,
  selected,
  onChange,
}: {
  controls: DocumentControl[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const linked = controls.filter((c) => selected.includes(c.id));
  const available = controls.filter((c) => !selected.includes(c.id));
  return (
    <div className="field">
      <label htmlFor="doc-controls">Controles de la norma que responde (opcional)</label>
      <div className="control-chips">
        {linked.map((c) => (
          <span className="control-chip" key={c.id} title={c.name}>
            {c.code}
            <button type="button" aria-label={`Quitar ${c.code}`} onClick={() => onChange(selected.filter((id) => id !== c.id))}>
              ×
            </button>
          </span>
        ))}
        <select
          id="doc-controls"
          value=""
          onChange={(e) => e.target.value && onChange([...selected, e.target.value])}
        >
          <option value="">+ vincular control…</option>
          {available.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} · {c.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function DocumentFormModal({
  token,
  areas,
  controls,
  existing,
  onClose,
  onSaved,
}: {
  token: string;
  areas: Area[];
  controls: DocumentControl[];
  existing?: DocumentDetail;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = existing != null;
  const [code, setCode] = useState(existing?.code ?? "");
  const [codeTouched, setCodeTouched] = useState(isEdit);
  const [title, setTitle] = useState(existing?.title ?? "");
  const [documentType, setDocumentType] = useState(existing?.document_type ?? "policy");
  const [file, setFile] = useState<File | null>(null);
  const [retentionMonths, setRetentionMonths] = useState(existing?.retention_months?.toString() ?? "");
  const [areaId, setAreaId] = useState(existing?.area?.id ?? "");
  const [implementationDate, setImplementationDate] = useState(existing?.implementation_date ?? "");
  const [reviewFrequency, setReviewFrequency] = useState(existing?.review_frequency_months?.toString() ?? "");
  const [nextReviewDate, setNextReviewDate] = useState(existing?.next_review_date ?? "");
  const [origin, setOrigin] = useState<DocumentOrigin>(existing?.origin ?? "internal");
  const [externalSource, setExternalSource] = useState(existing?.external_source ?? "");
  const [controlIds, setControlIds] = useState<string[]>(existing?.controls.map((c) => c.id) ?? []);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Numeración sugerida: solo mientras el usuario no haya tecleado el código.
  useEffect(() => {
    if (isEdit || codeTouched) return;
    let cancelled = false;
    api
      .nextDocumentCode(token, documentType)
      .then((res) => {
        if (!cancelled) setCode((prev) => (prev === "" || !codeTouched ? res.code : prev));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentType, isEdit, codeTouched]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!isEdit && !file) {
      setError("Selecciona un archivo para adjuntar");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const shared = {
        title,
        document_type: documentType,
        retention_months: retentionMonths ? Number(retentionMonths) : null,
        area_id: areaId || null,
        implementation_date: implementationDate || null,
        review_frequency_months: reviewFrequency ? Number(reviewFrequency) : null,
        next_review_date: nextReviewDate || null,
        origin,
        external_source: origin === "external" ? externalSource || null : null,
        control_ids: controlIds,
      };
      if (isEdit) {
        await api.updateDocument(token, existing.id, shared);
      } else {
        await api.createDocument(token, { code, file: file!, ...shared });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el documento");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? `Editar ${existing.code}` : "Nuevo documento"}</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          {!isEdit && (
            <div className="field">
              <label htmlFor="code">Código</label>
              <input
                id="code"
                required
                value={code}
                onChange={(e) => {
                  setCodeTouched(true);
                  setCode(e.target.value);
                }}
                placeholder="POL-001"
              />
              <div className="evidence-hint" style={{ marginTop: "0.3rem" }}>
                Consecutivo sugerido por tipo — se puede cambiar.
              </div>
            </div>
          )}
          <div className="field">
            <label htmlFor="title">Título</label>
            <input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="type">Tipo</label>
            <select id="type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            {!isEdit && DOCUMENT_TYPE_HINT[documentType] && (
              <div className="evidence-hint" style={{ marginTop: "0.3rem" }}>{DOCUMENT_TYPE_HINT[documentType]}</div>
            )}
          </div>
          {!isEdit && (
            <div className="field">
              <label htmlFor="file">Archivo</label>
              <input id="file" type="file" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
          )}
          <div className="field">
            <label htmlFor="doc-area">Área encargada (opcional)</label>
            <select id="doc-area" value={areaId} onChange={(e) => setAreaId(e.target.value)}>
              <option value="">— sin área —</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="doc-origin">Origen</label>
            <select id="doc-origin" value={origin} onChange={(e) => setOrigin(e.target.value as DocumentOrigin)}>
              <option value="internal">Interno</option>
              <option value="external">Externo (norma, contrato, proveedor)</option>
            </select>
          </div>
          {origin === "external" && (
            <div className="field">
              <label htmlFor="doc-source">Fuente / emisor externo</label>
              <input
                id="doc-source"
                value={externalSource}
                onChange={(e) => setExternalSource(e.target.value)}
                placeholder="ej. Consejo Nacional de Operación"
              />
            </div>
          )}
          <div className="field">
            <label htmlFor="impl-date">Fecha de implementación (opcional)</label>
            <input id="impl-date" type="date" value={implementationDate} onChange={(e) => setImplementationDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="review-freq">Frecuencia de revisión (meses, opcional)</label>
            <input
              id="review-freq"
              type="number"
              min={1}
              value={reviewFrequency}
              onChange={(e) => setReviewFrequency(e.target.value)}
            />
            <div className="evidence-hint" style={{ marginTop: "0.3rem" }}>
              Al aprobar una versión, la próxima revisión se reprograma sola con esta frecuencia.
            </div>
          </div>
          <div className="field">
            <label htmlFor="next-review">Próxima revisión (opcional)</label>
            <input id="next-review" type="date" value={nextReviewDate} onChange={(e) => setNextReviewDate(e.target.value)} />
          </div>
          <ControlPicker controls={controls} selected={controlIds} onChange={setControlIds} />
          <div className="field">
            <label htmlFor="retention">Retención (meses, opcional)</label>
            <input
              id="retention"
              type="number"
              min={1}
              value={retentionMonths}
              onChange={(e) => setRetentionMonths(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Guardando…" : isEdit ? "Guardar" : "Crear"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function NewVersionModal({
  token,
  documentId,
  onClose,
  onCreated,
}: {
  token: string;
  documentId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [changeSummary, setChangeSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Selecciona un archivo para adjuntar");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await api.createVersion(token, documentId, { file, change_summary: changeSummary });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la nueva versión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nueva versión</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="v-file">Archivo</label>
            <input id="v-file" type="file" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
          <div className="field">
            <label htmlFor="change-summary">Resumen del cambio (obligatorio)</label>
            <textarea
              id="change-summary"
              rows={3}
              required
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Creando…" : "Crear versión"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ReasonModal({
  title,
  label,
  confirmLabel,
  danger,
  onClose,
  onConfirm,
}: {
  title: string;
  label: string;
  confirmLabel: string;
  danger?: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [text, setText] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    onConfirm(text.trim());
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="reason-text">{label}</label>
            <textarea id="reason-text" rows={3} required value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className={danger ? "btn btn-danger" : "btn btn-primary"}>
              {confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AreasModal({
  token,
  areas,
  onChanged,
  onClose,
}: {
  token: string;
  areas: Area[];
  onChanged: () => void;
  onClose: () => void;
}) {
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.directory(token).then(setDirectory).catch(() => {});
  }, [token]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Áreas del tenant</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          El área encargada de cada documento, proceso o control documentado. Su gerente
          firma el primer paso de la aprobación multinivel; seguridad de la información
          (Admin del tenant) firma el segundo y publica.
        </p>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {areas.length === 0 ? (
          <div className="empty-state">Todavía no hay áreas definidas.</div>
        ) : (
          <div className="stacked" style={{ marginBottom: "1rem" }}>
            {areas.map((a) => (
              <div key={a.id} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <strong style={{ flex: 1 }}>{a.name}</strong>
                <select
                  value={a.manager_user_id ?? ""}
                  disabled={busy}
                  aria-label={`Gerente de ${a.name}`}
                  onChange={(e) =>
                    run(() => api.updateArea(token, a.id, { manager_user_id: e.target.value || null }))
                  }
                >
                  <option value="">— sin gerente —</option>
                  {directory.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}

        <form
          className="stacked"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newName.trim()) return;
            run(() => api.createArea(token, { name: newName.trim() })).then(() => setNewName(""));
          }}
        >
          <div className="field">
            <label htmlFor="new-area">Nueva área</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input
                id="new-area"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="ej. Tecnología, Talento Humano"
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn btn-primary" disabled={busy || !newName.trim()}>
                Agregar
              </button>
            </div>
          </div>
        </form>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}
