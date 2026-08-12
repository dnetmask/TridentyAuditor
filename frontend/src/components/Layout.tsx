import { NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Layout() {
  const { session, logout } = useAuth();

  if (!session) return <Navigate to="/entrar" replace />;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <NavLink to="/ruta-sgsi" className="topbar-brand">
            TridentyAuditor <small>GRC</small>
          </NavLink>
          <nav className="topbar-nav">
            <NavLink to="/ruta-sgsi" className={({ isActive }) => (isActive ? "active" : "")}>
              Ruta SGSI
            </NavLink>
            <NavLink to="/documentos" className={({ isActive }) => (isActive ? "active" : "")}>
              Documentos
            </NavLink>
            <NavLink to="/marco-normativo" className={({ isActive }) => (isActive ? "active" : "")}>
              Marco normativo
            </NavLink>
          </nav>
        </div>
        <div className="topbar-session">
          <span className="tier-chip">{session.tenantName}</span>
          <span>
            <strong>{session.sub}</strong> · {session.role}
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
