import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Tenant } from "../api/types";

export function AdminTenantsPage() {
  const { session } = useAuth();
  const token = session!.token;

  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTenantAdminFor, setNewTenantAdminFor] = useState<Tenant | null>(null);

  async function reload() {
    try {
      setTenants(await api.listTenants(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de tenants");
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Tenants</h1>
          <p>
            Alta y administración de clientes de Netmask. Super Admin no tiene
            acceso a los documentos ni al SGSI de ningún tenant — solo los
            aprovisiona (sección 07 del documento de arquitectura).
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nuevo tenant
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="card">
        {tenants === null ? (
          <div className="empty-state">Cargando…</div>
        ) : tenants.length === 0 ? (
          <div className="empty-state">Todavía no hay tenants creados.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Slug</th>
                <th>Aislamiento</th>
                <th>Creado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id}>
                  <td>{t.name}</td>
                  <td><code>{t.slug}</code></td>
                  <td><span className="tier-chip">{t.isolation_tier}</span></td>
                  <td>{new Date(t.created_at).toLocaleDateString()}</td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => setNewTenantAdminFor(t)}>
                      + Admin
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateTenantModal
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={async (tenant) => {
            setShowCreate(false);
            await reload();
            setNewTenantAdminFor(tenant);
          }}
        />
      )}

      {newTenantAdminFor && (
        <CreateTenantAdminModal
          token={token}
          tenant={newTenantAdminFor}
          onClose={() => setNewTenantAdminFor(null)}
          onCreated={() => setNewTenantAdminFor(null)}
        />
      )}
    </div>
  );
}

function CreateTenantModal({
  token,
  onClose,
  onCreated,
}: {
  token: string;
  onClose: () => void;
  onCreated: (tenant: Tenant) => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tenant = await api.createTenant(token, name, slug);
      onCreated(tenant);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el tenant");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo tenant</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="t-name">Nombre</label>
            <input id="t-name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme S.A.S." />
          </div>
          <div className="field">
            <label htmlFor="t-slug">Slug</label>
            <input
              id="t-slug"
              required
              pattern="[a-z0-9\-]+"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="acme"
            />
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

function CreateTenantAdminModal({
  token,
  tenant,
  onClose,
  onCreated,
}: {
  token: string;
  tenant: Tenant;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createUser(token, {
        email,
        password,
        full_name: fullName,
        role: "tenant_admin",
        tenant_id: tenant.id,
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Admin del tenant · {tenant.name}</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        {done ? (
          <>
            <p>Cuenta creada. Comparte estas credenciales de forma segura con el cliente.</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" onClick={onCreated}>Listo</button>
            </div>
          </>
        ) : (
          <form className="stacked" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="ta-email">Email</label>
              <input id="ta-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ta-name">Nombre completo</label>
              <input id="ta-name" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ta-password">Contraseña temporal</label>
              <input
                id="ta-password"
                type="text"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Creando…" : "Crear admin"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
