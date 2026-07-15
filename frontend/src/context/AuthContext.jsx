import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  clearTokens,
  getAccessToken,
  getMe,
  login as apiLogin,
  setOnAuthExpired,
  setTokens,
  signup as apiSignup,
} from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" until we know whether the stored access token (if any) is
  // still valid, so ProtectedRoute doesn't flash-redirect to /login on
  // every page refresh.
  const [status, setStatus] = useState("checking");

  const loadCurrentUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }
    try {
      const res = await getMe();
      setUser(res.data);
      setStatus("authenticated");
    } catch {
      // The response interceptor already tried refreshing once; if we're
      // still here the session is genuinely gone.
      clearTokens();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
    // Wired up so a failed silent-refresh anywhere in the app (not just
    // this initial check) drops the user back to the login screen.
    setOnAuthExpired(() => {
      setUser(null);
      setStatus("unauthenticated");
    });
  }, [loadCurrentUser]);

  const login = async (email, password) => {
    const res = await apiLogin(email, password);
    setTokens(res.data);
    await loadCurrentUser();
  };

  const signup = async (email, password, name) => {
    await apiSignup(email, password, name);
    // Signup doesn't return tokens, so log in right after.
    await login(email, password);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    setStatus("unauthenticated");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isAuthenticated: status === "authenticated",
        isChecking: status === "checking",
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
