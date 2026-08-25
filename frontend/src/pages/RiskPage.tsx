import { Fragment, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { RiskLevelBadge } from "../components/RiskLevelBadge";
import type {
  Asset,
  AssetCategory,
  DirectoryUser,
  DocumentDetail,
  Risk,
  RiskStatus,
  TreatmentDecision,
} from "../api/types";

const CATEGORY_LABEL: Record<AssetCategory, string> = {
  information: "Información",
  software: "Software",
  hardware: "Hardware",
  service: "Servicio",
  people: "Personas",
  facility: "Instalación",
  other: "Otro",
};

const TREATMENT_LABEL: Record<TreatmentDecision, string> = {
  mitigate: "Mitigar",
  accept: "Aceptar",
  transfer: "Transferir",
  avoid: "Evitar",
};

const STATUS_LABEL: Record<RiskStatus, string> = {
  open: "Abierto",
  treating: "En tratamiento",
  closed: "Cerrado",
};

interface ControlOption {
  id: string;
  code: string;
  name: string;
}

export function RiskPage() {
  const { session } = useAuth();
  const token = session!.token;
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";

  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [risks, setRisks] = useState<Risk[] | null>(null);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [controls, setControls] = useState<ControlOption[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreateAsset, setShowCreateAsset] = useState(false);
  const [showCreateRisk, setShowCreateRisk] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [assetsData, risksData] = await Promise.all([api.listAssets(token), api.listRisks(token)]);
    setAssets(assetsData);
    setRisks(risksData);
  }

  useEffect(() => {
    reload();
    api.directory(token).then(setDirectory).catch(() => {});
    api.listDocuments(token).then(setDocuments).catch(() => {});
    api
      .getFramework(session!.frameworkCode!)
      .then((fw) =>
        setControls(fw.domains.flatMap((d) => d.controls.map((c) => ({ id: c.id, code: c.code, name: c.name })))),
      )
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(action: () => Promise<unknown>) {
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

  const assetName = (id: string | null) => assets?.find((a) => a.id === id)?.name ?? "—";
  const approvedDocuments = useMemo(
    () => documents.filter((d) => d.versions.some((v) => v.status === "approved")),
    [documents],
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Gestión de riesgos</h1>
          <p>
            MOD·RSK — inventario de activos y matriz de riesgo. Probabilidad × impacto
            (1-5 cada una) calcula el nivel inherente; el tratamiento y el riesgo
            residual se registran por separado.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="page-header" style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Activos</h2>
        {canWrite && (
          <button className="btn btn-secondary btn-sm" onClick={() => setShowCreateAsset(true)}>
            + Nuevo activo
          </button>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        {assets === null ? (
          <div className="empty-state">Cargando…</div>
        ) : assets.length === 0 ? (
          <div className="empty-state">Sin activos todavía.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Categoría</th>
                <th>Dueño</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>{CATEGORY_LABEL[a.category]}</td>
                  <td>{directory.find((u) => u.id === a.owner_user_id)?.full_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="page-header" style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Matriz de riesgo</h2>
        {canWrite && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreateRisk(true)}>
            + Nuevo riesgo
          </button>
        )}
      </div>

      <div className="card">
        {risks === null ? (
          <div className="empty-state">Cargando…</div>
        ) : risks.length === 0 ? (
          <div className="empty-state">Sin riesgos registrados todavía.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Riesgo</th>
                <th>Activo</th>
                <th>Inherente</th>
                <th>Tratamiento</th>
                <th>Residual</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {risks.map((r) => (
                <Fragment key={r.id}>
                  <tr className="clickable" onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}>
                    <td>{r.title}</td>
                    <td>{assetName(r.asset_id)}</td>
                    <td>
                      {r.likelihood}×{r.impact}={r.inherent_score} <RiskLevelBadge level={r.inherent_level} />
                    </td>
                    <td>{r.treatment_decision ? TREATMENT_LABEL[r.treatment_decision] : "—"}</td>
                    <td>
                      {r.residual_level ? (
                        <>
                          {r.residual_likelihood}×{r.residual_impact}={r.residual_score}{" "}
                          <RiskLevelBadge level={r.residual_level} />
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{STATUS_LABEL[r.status]}</td>
                  </tr>
                  {expandedId === r.id && (
                    <tr>
                      <td colSpan={6} style={{ padding: 0 }}>
                        <RiskDetailPanel
                          risk={r}
                          assets={assets ?? []}
                          directory={directory}
                          documents={approvedDocuments}
                          controls={controls}
                          canWrite={canWrite}
                          busy={busy}
                          onUpdate={(payload) => run(() => api.updateRisk(token, r.id, payload))}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreateAsset && (
        <CreateAssetModal
          token={token}
          directory={directory}
          onClose={() => setShowCreateAsset(false)}
          onCreated={async () => {
            setShowCreateAsset(false);
            await reload();
          }}
        />
      )}

      {showCreateRisk && (
        <CreateRiskModal
          token={token}
          assets={assets ?? []}
          onClose={() => setShowCreateRisk(false)}
          onCreated={async () => {
            setShowCreateRisk(false);
            await reload();
          }}
        />
      )}
    </div>
  );
}

function RiskDetailPanel({
  risk,
  assets,
  directory,
  documents,
  controls,
  canWrite,
  busy,
  onUpdate,
}: {
  risk: Risk;
  assets: Asset[];
  directory: DirectoryUser[];
  documents: DocumentDetail[];
  controls: ControlOption[];
  canWrite: boolean;
  busy: boolean;
  onUpdate: (payload: Record<string, unknown>) => void;
}) {
  const [treatmentPlan, setTreatmentPlan] = useState(risk.treatment_plan ?? "");
  const disabled = busy || !canWrite;
  const linkedControls = controls.filter((c) => risk.control_ids.includes(c.id));
  const availableControls = controls.filter((c) => !risk.control_ids.includes(c.id));

  return (
    <div className="risk-detail-panel">
      <div className="risk-detail-grid">
        <div className="field">
          <label>Activo</label>
          <select
            value={risk.asset_id ?? ""}
            disabled={disabled}
            onChange={(e) => onUpdate({ asset_id: e.target.value || null })}
          >
            <option value="">— sin activo —</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Dueño del riesgo</label>
          <select
            value={risk.owner_user_id ?? ""}
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
          <label>Estado</label>
          <select value={risk.status} disabled={disabled} onChange={(e) => onUpdate({ status: e.target.value })}>
            {Object.entries(STATUS_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Decisión de tratamiento</label>
          <select
            value={risk.treatment_decision ?? ""}
            disabled={disabled}
            onChange={(e) => onUpdate({ treatment_decision: e.target.value || null })}
          >
            <option value="">— sin definir —</option>
            {Object.entries(TREATMENT_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Probabilidad residual</label>
          <select
            value={risk.residual_likelihood ?? ""}
            disabled={disabled}
            onChange={(e) => e.target.value && onUpdate({ residual_likelihood: Number(e.target.value) })}
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Impacto residual</label>
          <select
            value={risk.residual_impact ?? ""}
            disabled={disabled}
            onChange={(e) => e.target.value && onUpdate({ residual_impact: Number(e.target.value) })}
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Evidencia del tratamiento</label>
          <select
            value={risk.evidence_document_id ?? ""}
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
        <label>Plan de tratamiento</label>
        <textarea
          rows={2}
          value={treatmentPlan}
          disabled={disabled}
          onChange={(e) => setTreatmentPlan(e.target.value)}
          onBlur={() => treatmentPlan !== (risk.treatment_plan ?? "") && onUpdate({ treatment_plan: treatmentPlan })}
        />
        <div className="evidence-hint" style={{ marginTop: "0.3rem" }}>
          <strong>Evidencia sugerida:</strong> algo que demuestre que el tratamiento se aplicó de
          verdad — captura de una configuración, contrato o SLA firmado, informe de una prueba,
          ticket de cambio cerrado. Si el tratamiento trata un control de tu norma, revisa también
          la guía de evidencia de ese control en SoA o Marco normativo.
        </div>
      </div>

      <div className="field">
        <label>Controles que tratan este riesgo</label>
        <div className="control-chips">
          {linkedControls.map((c) => (
            <span className="control-chip" key={c.id}>
              {c.code}
              {canWrite && (
                <button
                  disabled={busy}
                  onClick={() => onUpdate({ control_ids: risk.control_ids.filter((id) => id !== c.id) })}
                  title="Quitar"
                >
                  ×
                </button>
              )}
            </span>
          ))}
          {canWrite && availableControls.length > 0 && (
            <select
              value=""
              disabled={busy}
              onChange={(e) => e.target.value && onUpdate({ control_ids: [...risk.control_ids, e.target.value] })}
            >
              <option value="">+ vincular control…</option>
              {availableControls.map((c) => (
                <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>
    </div>
  );
}

function CreateAssetModal({
  token,
  directory,
  onClose,
  onCreated,
}: {
  token: string;
  directory: DirectoryUser[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<AssetCategory>("information");
  const [ownerUserId, setOwnerUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createAsset(token, { name, category, owner_user_id: ownerUserId || null });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el activo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo activo</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="a-name">Nombre</label>
            <input id="a-name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="a-category">Categoría</label>
            <select id="a-category" value={category} onChange={(e) => setCategory(e.target.value as AssetCategory)}>
              {Object.entries(CATEGORY_LABEL).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="a-owner">Dueño</label>
            <select id="a-owner" value={ownerUserId} onChange={(e) => setOwnerUserId(e.target.value)}>
              <option value="">— sin dueño —</option>
              {directory.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </select>
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

function CreateRiskModal({
  token,
  assets,
  onClose,
  onCreated,
}: {
  token: string;
  assets: Asset[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [assetId, setAssetId] = useState("");
  const [threat, setThreat] = useState("");
  const [vulnerability, setVulnerability] = useState("");
  const [likelihood, setLikelihood] = useState(3);
  const [impact, setImpact] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createRisk(token, {
        title,
        asset_id: assetId || null,
        threat: threat || null,
        vulnerability: vulnerability || null,
        likelihood,
        impact,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el riesgo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo riesgo</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="r-title">Título</label>
            <input id="r-title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="r-asset">Activo</label>
            <select id="r-asset" value={assetId} onChange={(e) => setAssetId(e.target.value)}>
              <option value="">— sin activo —</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="r-threat">Amenaza</label>
            <input id="r-threat" value={threat} onChange={(e) => setThreat(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="r-vuln">Vulnerabilidad</label>
            <input id="r-vuln" value={vulnerability} onChange={(e) => setVulnerability(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="r-likelihood">Probabilidad (1-5)</label>
            <select id="r-likelihood" value={likelihood} onChange={(e) => setLikelihood(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="r-impact">Impacto (1-5)</label>
            <select id="r-impact" value={impact} onChange={(e) => setImpact(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
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
