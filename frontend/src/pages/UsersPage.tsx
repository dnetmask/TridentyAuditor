import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { User, UserRole } from "../api/types";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  tenant_admin: "Admin del tenant",
  internal_auditor: "Auditor interno",
  viewer: "Visualizador",
};

const ASSIGNABLE_ROLES: UserRole[] = ["tenant_admin", "internal_auditor", "viewer"];

export function UsersPage() {
  const { session } = useAuth();
  const token = session!.token;

  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);

  async function reload() {
    try {
      setUsers(await api.listUsers(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de usuarios");
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRoleChange(user: User, role: UserRole) {
    setBusy(true);
    setError(null);
    try {
      await api.updateUser(token, user.id, { role });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el rol");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleActive(user: User) {
    setBusy(true);
    setError(null);
    try {
      await api.updateUser(token, user.id, { is_active: !user.is_active });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el usuario");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Usuarios</h1>
          <p>
            Cuentas de tu tenant. Admin del tenant gestiona usuarios (sección 07
            del documento de arquitectura) — Auditor interno y Visualizador se
            crean desde aquí.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + Nuevo usuario
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="card">
        {users === null ? (
          <div className="empty-state">Cargando…</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>
                    {u.role === "super_admin" ? (
                      ROLE_LABEL[u.role]
                    ) : (
                      <select
                        value={u.role}
                        disabled={busy || u.id === session!.userId}
                        onChange={(e) => handleRoleChange(u, e.target.value as UserRole)}
                      >
                        {ASSIGNABLE_ROLES.map((r) => (
                          <option key={r} value={r}>{ROLE_LABEL[r]}</option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? "badge-approved" : "badge-obsolete"}`}>
                      {u.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={busy || u.id === session!.userId}
                      onClick={() => handleToggleActive(u)}
                    >
                      {u.is_active ? "Desactivar" : "Activar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateUserModal
          token={token}
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

function CreateUserModal({
  token,
  onClose,
  onCreated,
}: {
  token: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.createUser(token, { email, password, full_name: fullName, role });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo usuario</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="u-email">Email</label>
            <input id="u-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="u-name">Nombre completo</label>
            <input id="u-name" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="u-password">Contraseña temporal</label>
            <input
              id="u-password"
              type="text"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="u-role">Rol</label>
            <select id="u-role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
              {ASSIGNABLE_ROLES.map((r) => (
                <option key={r} value={r}>{ROLE_LABEL[r]}</option>
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
