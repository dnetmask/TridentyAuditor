import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { FrameworksPage } from "./pages/FrameworksPage";
import { WizardPage } from "./pages/WizardPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/entrar" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route path="/ruta-sgsi" element={<WizardPage />} />
            <Route path="/documentos" element={<DocumentsPage />} />
            <Route path="/marco-normativo" element={<FrameworksPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/ruta-sgsi" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
