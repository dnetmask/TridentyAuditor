import { Fragment, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useCompliance } from "../context/ComplianceContext";
import type {
  DirectoryUser,
  DocumentDetail,
  LegalComplianceRating,
  LegalRequirement,
  LegalRequirementStatus,
  LegalRequirementType,
  LegalSummary,
} from "../api/types";

const TYPE_LABELS: Record<LegalRequirementType, string> = {
  constitution: "Constitución",
  law: "Ley",
  decree: "Decreto",
  resolution: "Resolución",
  circular: "Circular",
  standard: "Norma / estándar",
  contract: "Contrato",
  guideline: "Guía",
  other: "Otro",
};

const RATING_LABELS: Record<LegalComplianceRating, string> = {
  not_evaluated: "Sin evaluar",
  compliant: "Cumple",
  partial: "Parcial",
  non_compliant: "No cumple",
};

const RATING_CLASS: Record<LegalComplianceRating, string> = {
  not_evaluated: "muted",
  compliant: "review-ok",
  partial: "review-soon",
  non_compliant: "review-overdue",
};

function daysUntil(isoDate: string): number {
  const target = new Date(`${isoDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

function ReviewDate({ date }: { date: string | null }) {
  if (!date) return <span className="muted">sin programar</span>;
  const days = daysUntil(date);
  if (days < 0) return <span className="review-overdue">vencida hace {-days} d</span>;
  if (days <= 30) return <span className="review-soon">en {days} d</span>;
  return (
    <span className="review-ok" title={date}>
      faltan {days} d
    </span>
  );
}

export function LegalPage() {
  const { session } = useAuth();
  const { refresh: refreshCompliance } = useCompliance();
  const token = session!.token;
  const canWrite = session!.role === "tenant_admin" || session!.role === "internal_auditor";

  const [requirements, setRequirements] = useState<LegalRequirement[] | null>(null);
  const [summary, setSummary] = useState<LegalSummary | null>(null);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState<{ existing?: LegalRequirement } | null>(null);
  const [busy, setBusy] = useState(false);

  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState<"" | LegalRequirementStatus>("in_force");
  const [filterRating, setFilterRating] = useState("");

  async function reload() {
    try {
      setRequirements(await api.listLegalRequirements(token));
      api.legalSummary(token).then(setSummary).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la matriz");
    }
  }

  useEffect(() => {
    reload();
    api.directory(token).then(setDirectory).catch(() => {});
    api.listDocuments(token).then(setDocuments).catch(() => {});
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

  const userName = (id: string | null) =>
    id ? directory.find((u) => u.id === id)?.full_name ?? "—" : null;
  const documentLabel = (id: string | null) => {
    if (!id) return null;
    const doc = documents.find((d) => d.id === id);
    return doc ? `${doc.code} · ${doc.title}` : "documento";
  };

  const filtered = useMemo(() => {
    if (requirements === null) return null;
    const text = search.trim().toLowerCase();
    return requirements.filter((r) => {
      if (filterStatus && r.status !== filterStatus) return false;
      if (filterType && r.requirement_type !== filterType) return false;
      if (filterRating && r.compliance_rating !== filterRating) return false;
      if (
        text &&
        ![r.name, r.topic ?? "", r.issuer ?? "", r.description ?? ""].some((v) =>
          v.toLowerCase().includes(text),
        )
      ) {
        return false;
      }
      return true;
    });
  }, [requirements, search, filterType, filterStatus, filterRating]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Matriz de requisitos legales</h1>
          <p>
            MOD·LEG — requisitos legales, regulatorios y contractuales que aplican al
            tenant (ISO 27001 cl. 4 y control A.5.31), con responsable, evidencia de
            aplicación y calificación de cumplimiento.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {summary && summary.total > 0 && (
            <span title={`${summary.compliant} cumplen · ${summary.partial} parcial · ${summary.non_compliant} no cumplen · ${summary.not_evaluated} sin evaluar`}>
              Nivel de cumplimiento: <strong>{summary.percentage}%</strong>
            </span>
          )}
          {canWrite && (
            <button className="btn btn-primary" onClick={() => setShowForm({})}>
              + Nuevo requisito
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <input
            type="search"
            placeholder="Buscar nombre, tema o emisor…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} aria-label="Filtrar por tipo">
            <option value="">Todos los tipos</option>
            {Object.entries(TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
            aria-label="Filtrar por estado"
          >
            <option value="in_force">Vigentes</option>
            <option value="repealed">Derogados</option>
            <option value="">Todos</option>
          </select>
          <select
            value={filterRating}
            onChange={(e) => setFilterRating(e.target.value)}
            aria-label="Filtrar por calificación"
          >
            <option value="">Todas las calificaciones</option>
            {Object.entries(RATING_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {filtered === null ? (
          <div className="empty-state">Cargando…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            {requirements && requirements.length > 0
              ? "Ningún requisito coincide con los filtros."
              : "La matriz está vacía — registra el primer requisito legal que aplica a la organización."}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Requisito</th>
                <th>Tema</th>
                <th>Responsable</th>
                <th>Próx. revisión</th>
                <th>Calificación</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const isOpen = expandedId === r.id;
                return (
                  <Fragment key={r.id}>
                    <tr className="clickable" onClick={() => setExpandedId(isOpen ? null : r.id)}>
                      <td>{TYPE_LABELS[r.requirement_type]}</td>
                      <td>
                        <strong>{r.name}</strong>
                        {(r.issuer || r.publication_year) && (
                          <div className="muted" style={{ fontSize: "0.82rem" }}>
                            {r.issuer ?? ""}{r.issuer && r.publication_year ? " · " : ""}{r.publication_year ?? ""}
                          </div>
                        )}
                      </td>
                      <td>{r.topic ?? <span className="muted">—</span>}</td>
                      <td>{userName(r.responsible_user_id) ?? <span className="muted">—</span>}</td>
                      <td>
                        {r.status === "repealed" ? <span className="muted">—</span> : <ReviewDate date={r.next_review_date} />}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {r.status === "repealed" ? (
                          <span className="retired-badge">Derogado</span>
                        ) : canWrite ? (
                          <select
                            value={r.compliance_rating}
                            disabled={busy}
                            aria-label={`Calificación de ${r.name}`}
                            onChange={(e) =>
                              runAction(() =>
                                api.updateLegalRequirement(token, r.id, {
                                  compliance_rating: e.target.value as LegalComplianceRating,
                                }),
                              )
                            }
                          >
                            {Object.entries(RATING_LABELS).map(([value, label]) => (
                              <option key={value} value={value}>{label}</option>
                            ))}
                          </select>
                        ) : (
                          <span className={RATING_CLASS[r.compliance_rating]}>
                            {RATING_LABELS[r.compliance_rating]}
                          </span>
                        )}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={6} style={{ padding: 0 }}>
                          <div className="doc-detail-panel">
                            <div className="doc-meta-row">
                              {r.articles && <div><strong>Artículos:</strong> {r.articles}</div>}
                              {r.description && <div className="muted">{r.description}</div>}
                              {r.application_evidence && (
                                <div><strong>Cómo se aplica:</strong> {r.application_evidence}</div>
                              )}
                              <div className="muted">
                                {r.evidence_document_id
                                  ? `Evidencia: ${documentLabel(r.evidence_document_id)}`
                                  : "Sin documento de evidencia vinculado"}
                                {r.review_frequency_months
                                  ? ` · revisión cada ${r.review_frequency_months} meses`
                                  : ""}
                                {r.expiration_date ? ` · vence el ${r.expiration_date}` : " · sin vencimiento"}
                              </div>
                              {canWrite && (
                                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                                  <button
                                    className="btn btn-secondary btn-sm"
                                    disabled={busy}
                                    onClick={() => setShowForm({ existing: r })}
                                  >
                                    Editar
                                  </button>
                                  <button
                                    className={r.status === "in_force" ? "btn btn-danger btn-sm" : "btn btn-secondary btn-sm"}
                                    disabled={busy}
                                    onClick={() =>
                                      runAction(() =>
                                        api.updateLegalRequirement(token, r.id, {
                                          status: r.status === "in_force" ? "repealed" : "in_force",
                                        }),
                                      )
                                    }
                                  >
                                    {r.status === "in_force" ? "Marcar derogado" : "Reactivar"}
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
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

      {showForm && (
        <RequirementFormModal
          token={token}
          existing={showForm.existing}
          directory={directory}
          documents={documents}
          onClose={() => setShowForm(null)}
          onSaved={async () => {
            setShowForm(null);
            await reload();
            refreshCompliance();
          }}
        />
      )}
    </div>
  );
}

function RequirementFormModal({
  token,
  existing,
  directory,
  documents,
  onClose,
  onSaved,
}: {
  token: string;
  existing?: LegalRequirement;
  directory: DirectoryUser[];
  documents: DocumentDetail[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = existing != null;
  const [requirementType, setRequirementType] = useState<LegalRequirementType>(
    existing?.requirement_type ?? "law",
  );
  const [name, setName] = useState(existing?.name ?? "");
  const [issuer, setIssuer] = useState(existing?.issuer ?? "");
  const [publicationYear, setPublicationYear] = useState(existing?.publication_year?.toString() ?? "");
  const [articles, setArticles] = useState(existing?.articles ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [topic, setTopic] = useState(existing?.topic ?? "");
  const [responsibleId, setResponsibleId] = useState(existing?.responsible_user_id ?? "");
  const [evidenceId, setEvidenceId] = useState(existing?.evidence_document_id ?? "");
  const [applicationEvidence, setApplicationEvidence] = useState(existing?.application_evidence ?? "");
  const [reviewFrequency, setReviewFrequency] = useState(
    existing?.review_frequency_months?.toString() ?? "",
  );
  const [nextReviewDate, setNextReviewDate] = useState(existing?.next_review_date ?? "");
  const [expirationDate, setExpirationDate] = useState(existing?.expiration_date ?? "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Igual que en el resto de módulos: solo documentos vigentes con versión
  // aprobada sirven como evidencia.
  const approvedDocuments = documents.filter(
    (d) => !d.retired_at && d.versions.some((v) => v.status === "approved"),
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = {
        requirement_type: requirementType,
        name,
        issuer: issuer || null,
        publication_year: publicationYear ? Number(publicationYear) : null,
        articles: articles || null,
        description: description || null,
        topic: topic || null,
        responsible_user_id: responsibleId || null,
        evidence_document_id: evidenceId || null,
        application_evidence: applicationEvidence || null,
        review_frequency_months: reviewFrequency ? Number(reviewFrequency) : null,
        next_review_date: nextReviewDate || null,
        expiration_date: expirationDate || null,
      };
      if (isEdit) {
        await api.updateLegalRequirement(token, existing.id, payload);
      } else {
        await api.createLegalRequirement(token, payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el requisito");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? `Editar ${existing.name}` : "Nuevo requisito legal"}</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="req-type">Tipo</label>
            <select
              id="req-type"
              value={requirementType}
              onChange={(e) => setRequirementType(e.target.value as LegalRequirementType)}
            >
              {Object.entries(TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="req-name">Nombre</label>
            <input
              id="req-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ej. Ley 1581 de 2012"
            />
          </div>
          <div className="field">
            <label htmlFor="req-issuer">Emisor (opcional)</label>
            <input
              id="req-issuer"
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
              placeholder="ej. Congreso de Colombia"
            />
          </div>
          <div className="field">
            <label htmlFor="req-year">Año de publicación (opcional)</label>
            <input
              id="req-year"
              type="number"
              min={1800}
              max={2200}
              value={publicationYear}
              onChange={(e) => setPublicationYear(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="req-articles">Artículo(s) que aplican (opcional)</label>
            <input
              id="req-articles"
              value={articles}
              onChange={(e) => setArticles(e.target.value)}
              placeholder='ej. "Art. 15" o "Toda la ley"'
            />
          </div>
          <div className="field">
            <label htmlFor="req-topic">Tema (opcional)</label>
            <input
              id="req-topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="ej. Protección de datos personales"
            />
          </div>
          <div className="field">
            <label htmlFor="req-description">Descripción (opcional)</label>
            <textarea
              id="req-description"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="req-responsible">Responsable (opcional)</label>
            <select id="req-responsible" value={responsibleId} onChange={(e) => setResponsibleId(e.target.value)}>
              <option value="">— sin responsable —</option>
              {directory.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="req-evidence">Documento de evidencia (opcional)</label>
            <select id="req-evidence" value={evidenceId} onChange={(e) => setEvidenceId(e.target.value)}>
              <option value="">— sin evidencia vinculada —</option>
              {approvedDocuments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code} · {d.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="req-application">Cómo se aplica (opcional)</label>
            <textarea
              id="req-application"
              rows={2}
              value={applicationEvidence}
              onChange={(e) => setApplicationEvidence(e.target.value)}
              placeholder="ej. Política de tratamiento de datos, avisos de privacidad"
            />
          </div>
          <div className="field">
            <label htmlFor="req-freq">Frecuencia de revisión (meses, opcional)</label>
            <input
              id="req-freq"
              type="number"
              min={1}
              value={reviewFrequency}
              onChange={(e) => setReviewFrequency(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="req-next">Próxima revisión (opcional)</label>
            <input id="req-next" type="date" value={nextReviewDate} onChange={(e) => setNextReviewDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="req-expiry">Vencimiento del requisito (opcional)</label>
            <input id="req-expiry" type="date" value={expirationDate} onChange={(e) => setExpirationDate(e.target.value)} />
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
