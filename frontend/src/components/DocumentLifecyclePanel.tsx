import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type {
  AcknowledgmentSummary,
  DirectoryUser,
  DispositionAction,
  DocumentDetail,
} from "../api/types";

/** Fase 5: distribución + acuse de recibo y retención/disposición de un
 *  documento. Se carga solo (su propio resumen de acuses) para no engordar
 *  DocumentsPage; avisa al padre con onChanged tras una acción que cambie la
 *  lista (derogación de facto, disposición). */
export function DocumentLifecyclePanel({
  token,
  doc,
  canWrite,
  canReview,
  directory,
  onChanged,
}: {
  token: string;
  doc: DocumentDetail;
  canWrite: boolean;
  canReview: boolean;
  directory: DirectoryUser[];
  onChanged: () => void;
}) {
  const [summary, setSummary] = useState<AcknowledgmentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPublish, setShowPublish] = useState(false);
  const [showDispose, setShowDispose] = useState(false);

  const hasApproved = doc.versions.some((v) => v.status === "approved");
  const disposed = doc.disposed_at != null;

  async function loadSummary() {
    try {
      setSummary(await api.documentAcknowledgments(token, doc.id));
    } catch {
      /* silencioso: el resumen es informativo */
    }
  }

  useEffect(() => {
    if (hasApproved) loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.id]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await loadSummary();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  const nameOf = (id: string) => directory.find((u) => u.id === id)?.full_name ?? id.slice(0, 8);

  if (disposed) {
    return (
      <div className="lifecycle-panel">
        <div className="alert alert-error">
          Documento {doc.disposition_action === "destroy" ? "destruido" : "archivado"} por{" "}
          {doc.disposed_by} — {doc.disposition_notes}
        </div>
      </div>
    );
  }

  return (
    <div className="lifecycle-panel">
      {error && <div className="alert alert-error" style={{ marginBottom: "0.5rem" }}>{error}</div>}

      {/* --- Distribución y acuse de recibo (solo con versión aprobada) --- */}
      {hasApproved && !doc.retired_at && (
        <div className="lifecycle-block">
          <div className="lifecycle-head">
            <strong>Acuse de recibo</strong>
            {summary && summary.total > 0 && (
              <span className="lifecycle-badge">
                {summary.acknowledged}/{summary.total} leído{summary.acknowledged === 1 ? "" : "s"}
              </span>
            )}
            {canWrite && (
              <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setShowPublish(true)}>
                Distribuir…
              </button>
            )}
          </div>
          {summary && summary.total > 0 ? (
            <ul className="ack-list">
              {summary.entries.map((e) => (
                <li key={e.id}>
                  {e.acknowledged_at ? "✓" : "○"} {nameOf(e.user_id)}
                  {e.acknowledged_at ? (
                    <span className="muted"> · leído el {new Date(e.acknowledged_at).toLocaleDateString()}</span>
                  ) : (
                    <span className="review-soon"> · pendiente</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <span className="muted">Aún no se ha distribuido a nadie.</span>
          )}
        </div>
      )}

      {/* --- Retención y disposición final --- */}
      <div className="lifecycle-block">
        <div className="lifecycle-head">
          <strong>Retención y disposición</strong>
          {doc.legal_hold && <span className="retired-badge">Retención legal</span>}
        </div>
        <div className="muted">
          {doc.retention_months
            ? `Retención ${doc.retention_months} meses · disposición: ${doc.disposition_date ?? "pendiente de aprobación"}`
            : "Sin periodo de retención definido."}
        </div>
        {canReview && (
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button
              className="btn btn-secondary btn-sm"
              disabled={busy}
              onClick={() => run(() => api.setLegalHold(token, doc.id, !doc.legal_hold))}
            >
              {doc.legal_hold ? "Levantar retención legal" : "Poner retención legal"}
            </button>
            <button
              className="btn btn-danger btn-sm"
              disabled={busy || doc.legal_hold}
              title={doc.legal_hold ? "Bajo retención legal: no se puede disponer" : undefined}
              onClick={() => setShowDispose(true)}
            >
              Disponer (archivar/destruir)
            </button>
          </div>
        )}
      </div>

      {showPublish && (
        <PublishModal
          directory={directory}
          alreadyAssigned={new Set(summary?.entries.map((e) => e.user_id) ?? [])}
          busy={busy}
          onClose={() => setShowPublish(false)}
          onConfirm={async (ids) => {
            setShowPublish(false);
            await run(() => api.publishDocument(token, doc.id, ids));
          }}
        />
      )}

      {showDispose && (
        <DisposeModal
          busy={busy}
          onClose={() => setShowDispose(false)}
          onConfirm={async (action, notes) => {
            setShowDispose(false);
            await run(() => api.disposeDocument(token, doc.id, action, notes));
          }}
        />
      )}
    </div>
  );
}

function PublishModal({
  directory,
  alreadyAssigned,
  busy,
  onClose,
  onConfirm,
}: {
  directory: DirectoryUser[];
  alreadyAssigned: Set<string>;
  busy: boolean;
  onClose: () => void;
  onConfirm: (userIds: string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Distribuir para acuse de recibo</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Los destinatarios verán el documento en "obligatorios sin leer" hasta marcarlo como
          leído y entendido. Solo se distribuye la versión aprobada vigente.
        </p>
        <div className="stacked" style={{ maxHeight: "40vh", overflowY: "auto" }}>
          {directory.map((u) => (
            <label key={u.id} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={selected.includes(u.id)}
                disabled={alreadyAssigned.has(u.id)}
                onChange={() => toggle(u.id)}
              />
              {u.full_name}
              {alreadyAssigned.has(u.id) && <span className="muted"> · ya asignado</span>}
            </label>
          ))}
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || selected.length === 0}
            onClick={() => onConfirm(selected)}
          >
            Distribuir a {selected.length}
          </button>
        </div>
      </div>
    </div>
  );
}

function DisposeModal({
  busy,
  onClose,
  onConfirm,
}: {
  busy: boolean;
  onClose: () => void;
  onConfirm: (action: DispositionAction, notes: string) => void;
}) {
  const [action, setAction] = useState<DispositionAction>("archive");
  const [notes, setNotes] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!notes.trim()) return;
    onConfirm(action, notes.trim());
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Disposición final</h2>
        <form className="stacked" onSubmit={submit}>
          <div className="field">
            <label htmlFor="disp-action">Acción</label>
            <select id="disp-action" value={action} onChange={(e) => setAction(e.target.value as DispositionAction)}>
              <option value="archive">Archivar</option>
              <option value="destroy">Destruir</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="disp-notes">Acta / motivo (queda registrado)</label>
            <textarea id="disp-notes" rows={3} required value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-danger" disabled={busy}>Confirmar disposición</button>
          </div>
        </form>
      </div>
    </div>
  );
}
