import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isChecking } = useAuth();
  const location = useLocation();

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center paper-texture">
        <Loader2 className="animate-spin text-ink-soft" size={28} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
