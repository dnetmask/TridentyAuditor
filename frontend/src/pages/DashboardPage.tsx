import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { DashboardOverview } from "../api/types";

function StatCard({
  to,
  label,
  value,
  hint,
  tone,
}: {
  to: string;
  label: string;
  value: number | string;
  hint?: string;
  tone?: "ok" | "warn" | "bad";
}) {
  return (
    <Link to={to} className={`stat-card${tone ? ` stat-${tone}` : ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </Link>
  );
}

export function DashboardPage() {
  const { session } = useAuth();
  const token = session!.token;
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [pendingReads, setPendingReads] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboardOverview(token)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el panel"));
    api.myAcknowledgments(token).then((acks) => setPendingReads(acks.length)).catch(() => {});
  }, [token]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Panel de {session!.tenantName ?? "la organización"}</h1>
          <p>
            Estado del SGSI de un vistazo — cumplimiento, documentos por vencer, riesgos,
            hallazgos y requisitos legales. Cada tarjeta lleva a su módulo.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      {data === null ? (
        <div className="card empty-state">Cargando…</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <div className="dashboard-compliance">
              <div className="dashboard-gauge">
                <span className="dashboard-gauge-value">{data.compliance.percentage}%</span>
                <span className="dashboard-gauge-label">Cumplimiento global</span>
              </div>
              <div className="dashboard-components">
                {data.compliance.components.map((c) => (
                  <div key={c.key} className="dashboard-component">
                    <div className="dashboard-component-head">
                      <span>{c.label}</span>
                      <strong>{c.percentage}%</strong>
                    </div>
                    <div className="dashboard-bar">
                      <div className="dashboard-bar-fill" style={{ width: `${c.percentage}%` }} />
                    </div>
                    <span className="stat-hint">{c.evidenced}/{c.total}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="stat-grid">
            <StatCard
              to="/documentos"
              label="Obligatorios sin leer"
              value={pendingReads}
              tone={pendingReads > 0 ? "bad" : "ok"}
              hint="documentos que debes acusar"
            />
            <StatCard
              to="/documentos"
              label="Documentos vigentes"
              value={data.documents.total_vigentes}
              hint={`${data.documents.pending_approval} en revisión`}
            />
            <StatCard
              to="/documentos"
              label="Revisiones vencidas"
              value={data.documents.review_overdue}
              tone={data.documents.review_overdue > 0 ? "bad" : "ok"}
              hint={`${data.documents.review_upcoming} próximas (≤30 d)`}
            />
            <StatCard
              to="/procesos"
              label="Procesos"
              value={data.processes.total}
              hint="mapa de procesos"
            />
            <StatCard
              to="/riesgos"
              label="Riesgos abiertos"
              value={data.risks.open}
              tone={data.risks.open > 0 ? "warn" : "ok"}
              hint={`${data.risks.total} en total`}
            />
            <StatCard
              to="/auditoria"
              label="Hallazgos abiertos"
              value={data.audits.findings_open}
              tone={data.audits.findings_open > 0 ? "warn" : "ok"}
              hint={`${data.audits.programs} auditorías`}
            />
            <StatCard
              to="/requisitos-legales"
              label="Requisitos legales"
              value={data.legal.total}
              hint={`${data.legal.compliant} cumplen · ${data.legal.non_compliant} no`}
            />
            <StatCard
              to="/soa"
              label="Controles aplicables (SoA)"
              value={data.soa.applicable}
              hint={`${data.soa.total} en la declaración`}
            />
          </div>

          <HygienePanel hygiene={data.documental_hygiene} />
        </>
      )}
    </div>
  );
}

function HygienePanel({ hygiene }: { hygiene: DashboardOverview["documental_hygiene"] }) {
  return (
    <div className="card" style={{ marginTop: "1.25rem" }}>
      <div className="page-header" style={{ marginBottom: "0.35rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.05rem" }}>Higiene documental</h2>
      </div>
      <p className="muted" style={{ marginTop: 0, fontSize: "0.84rem" }}>
        La lectura de "¿está al día?" — complementa, no reemplaza, el indicador de
        cumplimiento de arriba: aquí se mide vigencia y frescura, no madurez de
        implementación del SGSI.
      </p>
      <div className="hygiene-grid">
        <div className="hygiene-cell good">
          <div className="num">{hygiene.pct_current}%</div>
          <div className="lbl">Al día (de los programados)</div>
        </div>
        <div className={`hygiene-cell${hygiene.overdue > 0 ? " bad" : ""}`}>
          <div className="num">{hygiene.overdue}</div>
          <div className="lbl">Vencidos</div>
        </div>
        <div className={`hygiene-cell${hygiene.upcoming > 0 ? " warn" : ""}`}>
          <div className="num">{hygiene.upcoming}</div>
          <div className="lbl">Por vencer (≤30 d)</div>
        </div>
        <div className={`hygiene-cell${hygiene.unscheduled > 0 ? " warn" : ""}`}>
          <div className="num">{hygiene.unscheduled}</div>
          <div className="lbl">Sin revisión programada</div>
        </div>
        <div className="hygiene-cell">
          <div className="num">{hygiene.avg_implementation_days}</div>
          <div className="lbl">Días prom. de implementación</div>
        </div>
        <div className="hygiene-cell">
          <div className="num">{hygiene.total}</div>
          <div className="lbl">Documentos vigentes</div>
        </div>
      </div>
    </div>
  );
}
