import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Layout from "./components/Layout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import StatusPage from "./pages/StatusPage.jsx";
import ClaimsListPage from "./pages/ClaimsListPage.jsx";
import DocumentDataPage from "./pages/DocumentDataPage.jsx";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<UploadPage />} />
                  <Route path="/status" element={<StatusPage />} />
                  <Route path="/status/:claimId" element={<StatusPage />} />
                  <Route path="/claims" element={<ClaimsListPage />} />
                  <Route
                    path="/claims/:claimId"
                    element={<DocumentDataPage />}
                  />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
