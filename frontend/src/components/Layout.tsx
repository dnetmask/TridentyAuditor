import { NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../api/types";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  tenant_admin: "Admin del tenant",
  internal_auditor: "Auditor interno",
  viewer: "Visualizador",
};

export function Layout() {
  const { session, logout } = useAuth();

  if (!session) return <Navigate to="/entrar" replace />;

  const isSuperAdmin = session.role === "super_admin";
  const homePath = isSuperAdmin ? "/admin/tenants" : "/ruta-sgsi";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <NavLink to={homePath} className="topbar-brand">
            <img src="/logo.svg" alt="TridentyAuditor" className="topbar-logo" />
            <small>GRC</small>
          </NavLink>
          <nav className="topbar-nav">
            {isSuperAdmin ? (
              <NavLink to="/admin/tenants" className={({ isActive }) => (isActive ? "active" : "")}>
                Tenants
              </NavLink>
            ) : (
              <>
                <NavLink to="/ruta-sgsi" className={({ isActive }) => (isActive ? "active" : "")}>
                  Ruta SGSI
                </NavLink>
                <NavLink to="/riesgos" className={({ isActive }) => (isActive ? "active" : "")}>
                  Riesgos
                </NavLink>
                <NavLink to="/soa" className={({ isActive }) => (isActive ? "active" : "")}>
                  SoA
                </NavLink>
                <NavLink to="/documentos" className={({ isActive }) => (isActive ? "active" : "")}>
                  Documentos
                </NavLink>
                <NavLink to="/marco-normativo" className={({ isActive }) => (isActive ? "active" : "")}>
                  Marco normativo
                </NavLink>
                {session.role === "tenant_admin" && (
                  <NavLink to="/usuarios" className={({ isActive }) => (isActive ? "active" : "")}>
                    Usuarios
                  </NavLink>
                )}
              </>
            )}
          </nav>
        </div>
        <div className="topbar-session">
          {session.tenantName && <span className="tier-chip">{session.tenantName}</span>}
          <span>
            <strong>{session.fullName}</strong> · {ROLE_LABEL[session.role]}
          </span>
          <button className="btn btn-secondary btn-sm" onClick={logout}>
            Salir
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
