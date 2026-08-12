import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"new" | "existing">("new");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [adminToken, setAdminToken] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");

  const [existingTenantId, setExistingTenantId] = useState("");

  const [sub, setSub] = useState("auditor@netmask.co");
  const [role, setRole] = useState("tenant_admin");

  async function handleCreateAndEnter(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tenant = await api.createTenant(adminToken, tenantName, tenantSlug);
      const { access_token } = await api.mintDevToken(tenant.id, sub, role);
      login({ tenantId: tenant.id, tenantName: tenant.name, sub, role, token: access_token });
      navigate("/ruta-sgsi");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el tenant");
    } finally {
      setLoading(false);
    }
  }

  async function handleEnterExisting(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.mintDevToken(existingTenantId, sub, role);
      login({ tenantId: existingTenantId, tenantName: existingTenantId.slice(0, 8), sub, role, token: access_token });
      navigate("/ruta-sgsi");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo generar el token");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>TridentyAuditor</h1>
        <p className="subtitle">Plataforma GRC multitenant — acceso de desarrollo</p>

        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

        <div className="topbar-nav" style={{ marginBottom: "1rem" }}>
          <button
            type="button"
            className={mode === "new" ? "active" : ""}
            style={{ background: "none", border: "none", padding: "0.5rem 0.85rem", borderRadius: 8, cursor: "pointer" }}
            onClick={() => setMode("new")}
          >
            Crear tenant
          </button>
          <button
            type="button"
            className={mode === "existing" ? "active" : ""}
            style={{ background: "none", border: "none", padding: "0.5rem 0.85rem", borderRadius: 8, cursor: "pointer" }}
            onClick={() => setMode("existing")}
          >
            Usar tenant existente
          </button>
        </div>

        {mode === "new" ? (
          <form className="stacked" onSubmit={handleCreateAndEnter}>
            <div className="field">
              <label htmlFor="admin-token">Token de administrador Netmask</label>
              <input
                id="admin-token"
                type="password"
                required
                value={adminToken}
                onChange={(e) => setAdminToken(e.target.value)}
                placeholder="X-Admin-Token"
              />
              <span className="hint">Ver TRIDENTY_ADMIN_BOOTSTRAP_TOKEN en el backend.</span>
            </div>
            <div className="field">
              <label htmlFor="tenant-name">Nombre del tenant</label>
              <input
                id="tenant-name"
                required
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                placeholder="Acme S.A.S."
              />
            </div>
            <div className="field">
              <label htmlFor="tenant-slug">Slug</label>
              <input
                id="tenant-slug"
                required
                pattern="[a-z0-9\-]+"
                value={tenantSlug}
                onChange={(e) => setTenantSlug(e.target.value)}
                placeholder="acme"
              />
            </div>
            <LoginIdentityFields sub={sub} setSub={setSub} role={role} setRole={setRole} />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? "Creando…" : "Crear e ingresar"}
            </button>
          </form>
        ) : (
          <form className="stacked" onSubmit={handleEnterExisting}>
            <div className="field">
              <label htmlFor="tenant-id">ID del tenant</label>
              <input
                id="tenant-id"
                required
                value={existingTenantId}
                onChange={(e) => setExistingTenantId(e.target.value)}
                placeholder="uuid del tenant"
              />
            </div>
            <LoginIdentityFields sub={sub} setSub={setSub} role={role} setRole={setRole} />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? "Ingresando…" : "Ingresar"}
            </button>
          </form>
        )}

        <p className="dev-note">
          Sin Keycloak todavía (Fase 2 de la hoja de ruta): este formulario minta un
          JWT de desarrollo directamente contra el backend.
        </p>
      </div>
    </div>
  );
}

function LoginIdentityFields({
  sub,
  setSub,
  role,
  setRole,
}: {
  sub: string;
  setSub: (v: string) => void;
  role: string;
  setRole: (v: string) => void;
}) {
  return (
    <>
      <div className="field">
        <label htmlFor="sub">Usuario</label>
        <input id="sub" required value={sub} onChange={(e) => setSub(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="role">Rol</label>
        <select id="role" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="tenant_admin">Admin del tenant</option>
          <option value="control_owner">Dueño de control</option>
          <option value="internal_auditor">Auditor interno</option>
          <option value="collaborator">Colaborador</option>
        </select>
      </div>
    </>
  );
}
