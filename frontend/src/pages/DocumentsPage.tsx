import { Fragment, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/StatusBadge";
import type { DocumentDetail } from "../api/types";

const DOCUMENT_TYPES = [
  { value: "policy", label: "Política" },
  { value: "procedure", label: "Procedimiento" },
  { value: "record", label: "Registro" },
  { value: "other", label: "Otro" },
];

export function DocumentsPage() {
  const { session } = useAuth();
  const token = session!.token;

  const [documents, setDocuments] = useState<DocumentDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);

  async function reload() {
    try {
      setDocuments(await api.listDocuments(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de documentos");
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runAction(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Control documental</h1>
          <p>
            MOD·DOC — versionado y flujo de aprobación. Solo puede haber una copia
            vigente (<code>approved</code>) por documento; aprobar una versión nueva
            vuelve obsoleta a la anterior.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nuevo documento
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="card">
        {documents === null ? (
          <div className="empty-state">Cargando…</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">Todavía no hay documentos en este tenant.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Título</th>
                <th>Tipo</th>
                <th>Versión vigente</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const current = currentVersion(doc);
                const isOpen = expandedId === doc.id;
                return (
                  <Fragment key={doc.id}>
                    <tr
                      className="clickable"
                      onClick={() => setExpandedId(isOpen ? null : doc.id)}
                    >
                      <td><code>{doc.code}</code></td>
                      <td>{doc.title}</td>
                      <td>{DOCUMENT_TYPES.find((t) => t.value === doc.document_type)?.label ?? doc.document_type}</td>
                      <td>
                        {current ? (
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
                        <td colSpan={4} style={{ padding: 0 }}>
                          <DocumentDetailPanel
                            doc={doc}
                            token={token}
                            actor={session!.sub}
                            busy={busy}
                            onAction={runAction}
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
        <CreateDocumentModal
          token={token}
          defaultCreatedBy={session!.sub}
          onClose={() => setShowCreate(false)}
          onCreated={async () => {
            setShowCreate(false);
            await reload();
          }}
        />
      )}
    </div>
  );
}

function currentVersion(doc: DocumentDetail) {
  return [...doc.versions].sort((a, b) => b.version_number - a.version_number)[0] ?? null;
}

function DocumentDetailPanel({
  doc,
  token,
  actor,
  busy,
  onAction,
}: {
  doc: DocumentDetail;
  token: string;
  actor: string;
  busy: boolean;
  onAction: (action: () => Promise<unknown>) => Promise<void>;
}) {
  const [showNewVersion, setShowNewVersion] = useState(false);
  const hasOpenVersion = doc.versions.some((v) => v.status === "draft" || v.status === "in_review");
  const sorted = [...doc.versions].sort((a, b) => b.version_number - a.version_number);

  return (
    <div className="doc-detail-panel">
      {sorted.map((v) => (
        <div className="version-row" key={v.id}>
          <div className="version-meta">
            <span>
              <strong>v{v.version_number}</strong> · <StatusBadge status={v.status} />
            </span>
            <span className="muted">
              {v.storage_ref} · creado por {v.created_by}
              {v.approved_by ? ` · aprobado por ${v.approved_by}` : ""}
            </span>
            {v.change_summary && <span className="muted">{v.change_summary}</span>}
          </div>
          <div className="version-actions">
            {v.status === "draft" && (
              <button
                className="btn btn-secondary btn-sm"
                disabled={busy}
                onClick={() => onAction(() => api.submitForReview(token, doc.id, v.version_number))}
              >
                Enviar a revisión
              </button>
            )}
            {v.status === "in_review" && (
              <>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={busy}
                  onClick={() => onAction(() => api.approveVersion(token, doc.id, v.version_number, actor))}
                >
                  Aprobar
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  disabled={busy}
                  onClick={() => onAction(() => api.rejectVersion(token, doc.id, v.version_number, actor))}
                >
                  Rechazar
                </button>
              </>
            )}
          </div>
        </div>
      ))}

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

      {showNewVersion && (
        <NewVersionModal
          token={token}
          documentId={doc.id}
          defaultCreatedBy={actor}
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

function CreateDocumentModal({
  token,
  defaultCreatedBy,
  onClose,
  onCreated,
}: {
  token: string;
  defaultCreatedBy: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("policy");
  const [storageRef, setStorageRef] = useState("");
  const [retentionMonths, setRetentionMonths] = useState("");
  const [createdBy, setCreatedBy] = useState(defaultCreatedBy);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createDocument(token, {
        code,
        title,
        document_type: documentType,
        storage_ref: storageRef,
        created_by: createdBy,
        retention_months: retentionMonths ? Number(retentionMonths) : null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el documento");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo documento</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="code">Código</label>
            <input id="code" required value={code} onChange={(e) => setCode(e.target.value)} placeholder="POL-SGSI-001" />
          </div>
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
          </div>
          <div className="field">
            <label htmlFor="storage-ref">Referencia de almacenamiento</label>
            <input
              id="storage-ref"
              required
              value={storageRef}
              onChange={(e) => setStorageRef(e.target.value)}
              placeholder="s3://tenant/pol-sgsi-001-v1.pdf"
            />
          </div>
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
          <div className="field">
            <label htmlFor="created-by">Creado por</label>
            <input id="created-by" required value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} />
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

function NewVersionModal({
  token,
  documentId,
  defaultCreatedBy,
  onClose,
  onCreated,
}: {
  token: string;
  documentId: string;
  defaultCreatedBy: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [storageRef, setStorageRef] = useState("");
  const [changeSummary, setChangeSummary] = useState("");
  const [createdBy, setCreatedBy] = useState(defaultCreatedBy);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createVersion(token, documentId, {
        storage_ref: storageRef,
        created_by: createdBy,
        change_summary: changeSummary || null,
      });
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
            <label htmlFor="v-storage-ref">Referencia de almacenamiento</label>
            <input id="v-storage-ref" required value={storageRef} onChange={(e) => setStorageRef(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="change-summary">Resumen del cambio</label>
            <textarea id="change-summary" rows={3} value={changeSummary} onChange={(e) => setChangeSummary(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="v-created-by">Creado por</label>
            <input id="v-created-by" required value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} />
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
