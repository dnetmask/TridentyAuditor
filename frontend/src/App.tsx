import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { FrameworksPage } from "./pages/FrameworksPage";
import { WizardPage } from "./pages/WizardPage";
import { AdminTenantsPage } from "./pages/AdminTenantsPage";
import { UsersPage } from "./pages/UsersPage";
import { SoaPage } from "./pages/SoaPage";
import { RiskPage } from "./pages/RiskPage";
import type { UserRole } from "./api/types";

function RoleHome() {
  const { session } = useAuth();
  if (!session) return <Navigate to="/entrar" replace />;
  return <Navigate to={session.role === "super_admin" ? "/admin/tenants" : "/ruta-sgsi"} replace />;
}

function RequireRole({ roles, children }: { roles: UserRole[]; children: React.ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/entrar" replace />;
  if (!roles.includes(session.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/entrar" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route
              path="/admin/tenants"
              element={
                <RequireRole roles={["super_admin"]}>
                  <AdminTenantsPage />
                </RequireRole>
              }
            />
            <Route
              path="/usuarios"
              element={
                <RequireRole roles={["tenant_admin"]}>
                  <UsersPage />
                </RequireRole>
              }
            />
            <Route
              path="/ruta-sgsi"
              element={
                <RequireRole roles={["tenant_admin", "internal_auditor", "viewer"]}>
                  <WizardPage />
                </RequireRole>
              }
            />
            <Route
              path="/documentos"
              element={
                <RequireRole roles={["tenant_admin", "internal_auditor", "viewer"]}>
                  <DocumentsPage />
                </RequireRole>
              }
            />
            <Route
              path="/marco-normativo"
              element={
                <RequireRole roles={["tenant_admin", "internal_auditor", "viewer"]}>
                  <FrameworksPage />
                </RequireRole>
              }
            />
            <Route
              path="/soa"
              element={
                <RequireRole roles={["tenant_admin", "internal_auditor", "viewer"]}>
                  <SoaPage />
                </RequireRole>
              }
            />
            <Route
              path="/riesgos"
              element={
                <RequireRole roles={["tenant_admin", "internal_auditor", "viewer"]}>
                  <RiskPage />
                </RequireRole>
              }
            />
          </Route>
          <Route path="/" element={<RoleHome />} />
          <Route path="*" element={<RoleHome />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
