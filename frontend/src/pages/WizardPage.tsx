import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useCompliance } from "../context/ComplianceContext";
import type { DocumentDetail, PhaseProgress, WizardTask } from "../api/types";

const PHASE_STATUS_LABEL: Record<string, string> = {
  locked: "Bloqueada",
  current: "En curso",
  complete: "Completa",
};

export function WizardPage() {
  const { session } = useAuth();
  const { refresh: refreshCompliance } = useCompliance();
  const token = session!.token;
  const canInstantiate = session!.role === "tenant_admin";
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";

  const [progress, setProgress] = useState<PhaseProgress[] | null>(null);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [selectedPhaseId, setSelectedPhaseId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload(keepSelection = true) {
    const data = await api.wizardProgress(token);
    setProgress(data);
    if (!keepSelection || !selectedPhaseId) {
      const current = data.find((p) => p.status === "current") ?? data[0];
      setSelectedPhaseId(current?.phase.id ?? null);
    }
  }

  useEffect(() => {
    reload(false);
    api.listDocuments(token).then(setDocuments).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
      api.listDocuments(token).then(setDocuments).catch(() => {});
      refreshCompliance();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  const started = progress !== null && progress.some((p) => p.total_count > 0);
  const selectedPhase = progress?.find((p) => p.phase.id === selectedPhaseId) ?? null;
  const isCno = session!.frameworkCode === "CNO-1960";
  const routeLabel = isCno ? "Ruta CNO" : "Ruta SGSI";
  const routeDescription = isCno
    ? "las fases de puesta en marcha de la Guía de Ciberseguridad del CNO (Acuerdo 1960)"
    : "las 8 fases del ciclo de mejora continua";
  const cycleLabel = isCno ? "ciclo de cumplimiento CNO" : "ciclo SGSI";

  const approvedDocuments = useMemo(
    () => documents.filter((d) => d.versions.some((v) => v.status === "approved")),
    [documents],
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{routeLabel}</h1>
          <p>
            MOD·WZD — {routeDescription} convertidas en tareas con dueño, fecha y evidencia.
            Una fase no se desbloquea hasta que la anterior queda completa.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      {progress === null ? (
        <div className="card empty-state">Cargando…</div>
      ) : !started ? (
        <div className="card empty-state">
          <p>Este tenant todavía no ha iniciado su {cycleLabel}.</p>
          {canInstantiate ? (
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => run(() => api.wizardInstantiate(token))}
            >
              Comenzar {cycleLabel}
            </button>
          ) : (
            <p className="muted">Pídele al Admin del tenant que lo inicie.</p>
          )}
        </div>
      ) : (
        <div className="wizard-layout">
          <div className="wizard-steps">
            {progress.map((p) => (
              <button
                key={p.phase.id}
                className={[
                  "wizard-step",
                  `wizard-step-${p.status}`,
                  p.phase.id === selectedPhaseId ? "wizard-step-selected" : "",
                ].join(" ")}
                onClick={() => setSelectedPhaseId(p.phase.id)}
              >
                <span className="wizard-step-number">{p.status === "complete" ? "✓" : p.phase.number}</span>
                <span className="wizard-step-text">
                  <strong>{p.phase.name}</strong>
                  <span>
                    {PHASE_STATUS_LABEL[p.status]} · {p.done_count}/{p.total_count}
                  </span>
                </span>
              </button>
            ))}
          </div>

          {selectedPhase && (
            <div className="card wizard-panel">
              <div className="wizard-panel-header">
                <h2>
                  Fase {selectedPhase.phase.number} · {selectedPhase.phase.name}
                </h2>
                <p>{selectedPhase.phase.objective}</p>
              </div>
              {selectedPhase.status === "locked" && (
                <div className="alert alert-error" style={{ margin: "1rem 1.25rem" }}>
                  Esta fase está bloqueada hasta completar la anterior.
                </div>
              )}
              {selectedPhase.tasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  documents={approvedDocuments}
                  busy={busy}
                  readOnly={!canWrite}
                  onComplete={() => run(() => api.wizardCompleteTask(token, task.id))}
                  onReopen={() => run(() => api.wizardReopenTask(token, task.id))}
                  onUpdate={(payload) => run(() => api.wizardUpdateTask(token, task.id, payload))}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TaskRow({
  task,
  documents,
  busy,
  readOnly,
  onComplete,
  onReopen,
  onUpdate,
}: {
  task: WizardTask;
  documents: DocumentDetail[];
  busy: boolean;
  readOnly: boolean;
  onComplete: () => void;
  onReopen: () => void;
  onUpdate: (payload: { owner?: string | null; due_date?: string | null; evidence_document_id?: string | null }) => void;
}) {
  const [owner, setOwner] = useState(task.owner ?? "");
  const [dueDate, setDueDate] = useState(task.due_date ?? "");
  const done = task.status === "done";
  const fieldsDisabled = done || readOnly;

  return (
    <div className="task-row">
      <button
        className={`task-check ${done ? "task-check-done" : ""}`}
        disabled={busy || readOnly}
        title={readOnly ? "Tu rol no puede modificar tareas" : done ? "Reabrir" : "Marcar como completada"}
        onClick={done ? onReopen : onComplete}
      >
        {done ? "✓" : ""}
      </button>
      <div className="task-body">
        <div className="task-title-row">
          <strong className={done ? "done" : ""}>{task.title}</strong>
          {task.requires_evidence && <span className="evidence-required">Evidencia requerida</span>}
        </div>
        {task.description && (
          <div className="evidence-hint" style={{ marginBottom: "0.4rem" }}>
            <strong>Evidencia sugerida:</strong> {task.description}
          </div>
        )}
        <div className="task-fields">
          <input
            className="owner-input"
            placeholder="Dueño / responsable"
            value={owner}
            disabled={fieldsDisabled}
            onChange={(e) => setOwner(e.target.value)}
            onBlur={() => owner !== (task.owner ?? "") && onUpdate({ owner })}
          />
          <input
            className="due-input"
            type="date"
            value={dueDate}
            disabled={fieldsDisabled}
            onChange={(e) => setDueDate(e.target.value)}
            onBlur={() => dueDate !== (task.due_date ?? "") && onUpdate({ due_date: dueDate || null })}
          />
          <select
            className="evidence-select"
            value={task.evidence_document_id ?? ""}
            disabled={fieldsDisabled}
            onChange={(e) => onUpdate({ evidence_document_id: e.target.value || null })}
          >
            <option value="">— sin evidencia vinculada —</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} · {d.title}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
