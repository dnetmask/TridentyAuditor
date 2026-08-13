import { useState, type ReactNode } from "react";
import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ComplianceMeter } from "./ComplianceMeter";
import {
  IconRoute,
  IconRisk,
  IconChecklist,
  IconAudit,
  IconDocuments,
  IconBook,
  IconUsers,
  IconBuilding,
  IconChevronLeft,
  IconLogout,
} from "./icons";
import type { UserRole } from "../api/types";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  tenant_admin: "Admin del tenant",
  internal_auditor: "Auditor interno",
  viewer: "Visualizador",
};

const SIDEBAR_COLLAPSED_KEY = "tridenty.sidebarCollapsed";

type NavItem = { to: string; label: string; icon: ReactNode };

export function Layout() {
  const { session, logout } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1",
  );

  if (!session) return <Navigate to="/entrar" replace />;

  const isSuperAdmin = session.role === "super_admin";
  const homePath = isSuperAdmin ? "/admin/tenants" : "/ruta-sgsi";

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      return next;
    });
  }

  const navItems: NavItem[] = isSuperAdmin
    ? [{ to: "/admin/tenants", label: "Tenants", icon: <IconBuilding /> }]
    : [
        { to: "/ruta-sgsi", label: "Ruta SGSI", icon: <IconRoute /> },
        { to: "/riesgos", label: "Riesgos", icon: <IconRisk /> },
        { to: "/soa", label: "SoA", icon: <IconChecklist /> },
        { to: "/auditoria", label: "Auditoría", icon: <IconAudit /> },
        { to: "/documentos", label: "Documentos", icon: <IconDocuments /> },
        { to: "/marco-normativo", label: "Marco normativo", icon: <IconBook /> },
        ...(session.role === "tenant_admin"
          ? [{ to: "/usuarios", label: "Usuarios", icon: <IconUsers /> }]
          : []),
      ];

  const pageTitle = navItems.find((item) => item.to === location.pathname)?.label ?? "";

  return (
    <div className="app-shell">
      <aside className={`sidebar${collapsed ? " sidebar-collapsed" : ""}`}>
        <NavLink to={homePath} className="sidebar-brand">
          <img src="/logo.svg" alt="TridentyAuditor" className="sidebar-logo-full" />
          <div className="sidebar-logo-mono">T</div>
          <span className="sidebar-tagline">Gestión de cumplimiento (GRC)</span>
        </NavLink>

        {!isSuperAdmin && session.tenantName && (
          <div className="sidebar-tenant" title={session.tenantName}>
            <span className="sidebar-tenant-label">Tenant</span>
            <span className="sidebar-tenant-name">{session.tenantName}</span>
          </div>
        )}

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
              title={item.label}
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <button type="button" className="sidebar-collapse-toggle" onClick={toggleCollapsed}>
          <IconChevronLeft />
          <span>Contraer</span>
        </button>

        <div className="sidebar-footer">
          <div className="sidebar-user" title={`${session.fullName} · ${ROLE_LABEL[session.role]}`}>
            <strong>{session.fullName}</strong>
            <small>{ROLE_LABEL[session.role]}</small>
          </div>
          <button type="button" className="sidebar-logout" onClick={logout} title="Cerrar sesión">
            <IconLogout />
            <span>Salir</span>
          </button>
        </div>
      </aside>

      <div className="main-area">
        <header className="content-topbar">
          <span className="content-topbar-title">{pageTitle}</span>
          {!isSuperAdmin && <ComplianceMeter />}
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
