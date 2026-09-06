import { useState, type ReactNode } from "react";
import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { ComplianceMeter } from "./ComplianceMeter";
import { TridentMark, TridentyWordmark } from "./Brand";
import {
  IconRoute,
  IconRisk,
  IconChecklist,
  IconAudit,
  IconDocuments,
  IconBook,
  IconScale,
  IconDashboard,
  IconProcess,
  IconUsers,
  IconBuilding,
  IconChevronLeft,
  IconLogout,
  IconSun,
  IconMoon,
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
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1",
  );

  if (!session) return <Navigate to="/entrar" replace />;

  const isSuperAdmin = session.role === "super_admin";
  const homePath = isSuperAdmin ? "/admin/tenants" : "/panel";

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      return next;
    });
  }

  // El asistente paso a paso trae una ruta por norma (Ruta SGSI para ISO
  // 27001, Ruta CNO para CNO-1960 — ver docs/modules/mod-wzd.md); la etiqueta
  // del menú sigue la norma del tenant en sesión.
  const routeLabel = session?.frameworkCode === "CNO-1960" ? "Ruta CNO" : "Ruta SGSI";

  const navItems: NavItem[] = isSuperAdmin
    ? [{ to: "/admin/tenants", label: "Tenants", icon: <IconBuilding /> }]
    : [
        { to: "/panel", label: "Panel", icon: <IconDashboard /> },
        { to: "/ruta-sgsi", label: routeLabel, icon: <IconRoute /> },
        { to: "/procesos", label: "Procesos", icon: <IconProcess /> },
        { to: "/riesgos", label: "Riesgos", icon: <IconRisk /> },
        { to: "/soa", label: "SoA", icon: <IconChecklist /> },
        { to: "/auditoria", label: "Auditoría", icon: <IconAudit /> },
        { to: "/documentos", label: "Documentos", icon: <IconDocuments /> },
        { to: "/requisitos-legales", label: "Requisitos legales", icon: <IconScale /> },
        { to: "/marco-normativo", label: "Marco normativo", icon: <IconBook /> },
        ...(session.role === "tenant_admin"
          ? [{ to: "/usuarios", label: "Usuarios", icon: <IconUsers /> }]
          : []),
      ];

  const pageTitle = navItems.find((item) => item.to === location.pathname)?.label ?? "";

  return (
    <div className="app-shell">
      <aside className={`sidebar${collapsed ? " sidebar-collapsed" : ""}`}>
        <NavLink to={homePath} className="sidebar-brand" title="TridentyAuditor">
          <TridentMark className="sidebar-logomark" />
          <span className="sidebar-brand-text">
            <TridentyWordmark className="sidebar-wordmark" />
            <span className="sidebar-tagline">Auditor · Gestión de cumplimiento</span>
          </span>
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

        <button
          type="button"
          className="sidebar-theme-toggle"
          onClick={toggleTheme}
          title={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
        >
          {theme === "dark" ? <IconSun /> : <IconMoon />}
          <span>{theme === "dark" ? "Modo claro" : "Modo oscuro"}</span>
        </button>

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
