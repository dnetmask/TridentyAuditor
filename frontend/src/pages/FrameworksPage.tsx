import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Domain, FrameworkDetail } from "../api/types";

export function FrameworksPage() {
  const [framework, setFramework] = useState<FrameworkDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openDomain, setOpenDomain] = useState<string | null>(null);

  useEffect(() => {
    api
      .getFramework("ISO27001:2022")
      .then(setFramework)
      .catch((err) => setError(err instanceof ApiError ? err.message : "No se pudo cargar el framework"));
  }, []);

  const totalControls = framework?.domains.reduce((sum, d) => sum + d.controls.length, 0) ?? 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Marco normativo</h1>
          <p>
            Motor de frameworks: {framework?.name ?? "…"} — datos de referencia
            compartidos por todos los tenants, sin duplicar esquema por estándar.
          </p>
        </div>
        {framework && (
          <span className="tier-chip">
            {framework.domains.length} dominios · {totalControls} controles
          </span>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {!framework && !error && <div className="card empty-state">Cargando…</div>}

      {framework?.domains.map((domain) => (
        <DomainAccordion
          key={domain.id}
          domain={domain}
          open={openDomain === domain.id}
          onToggle={() => setOpenDomain(openDomain === domain.id ? null : domain.id)}
        />
      ))}
    </div>
  );
}

function DomainAccordion({ domain, open, onToggle }: { domain: Domain; open: boolean; onToggle: () => void }) {
  return (
    <div className="card domain-block">
      <div className="domain-header" onClick={onToggle}>
        <span className="domain-code">{domain.code}</span>
        <strong>{domain.name}</strong>
        <span className="domain-count">{domain.controls.length} controles {open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div className="control-list">
          {domain.controls.map((control) => (
            <div className="control-item" key={control.id}>
              <span className="control-code">{control.code}</span>
              <span>{control.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
