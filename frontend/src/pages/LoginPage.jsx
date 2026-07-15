import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Stamp, Loader2, AlertTriangle } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(email, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.detail || err?.message || "Could not log in."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen paper-texture flex items-center justify-center px-5 py-10">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-full bg-ink text-paper flex items-center justify-center rotate-[-6deg] shadow-sm mb-3">
            <Stamp size={22} strokeWidth={2} />
          </div>
          <h1 className="font-display text-2xl text-ink">Claim OCR</h1>
          <p className="text-[10px] tracking-[0.18em] uppercase text-ink-soft font-mono mt-1">
            Review Desk
          </p>
        </div>

        <div className="bg-white border border-ink/15 px-6 py-8">
          <h2 className="font-display text-xl text-ink mb-1">Sign in</h2>
          <p className="text-ink-soft text-sm mb-6">
            Log in to review and process claims.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <label className="block">
              <span className="text-xs font-mono uppercase tracking-wide text-ink-soft">
                Email
              </span>
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-1 w-full border border-ink/20 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-folder-dark"
              />
            </label>

            <label className="block">
              <span className="text-xs font-mono uppercase tracking-wide text-ink-soft">
                Password
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1 w-full border border-ink/20 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-folder-dark"
              />
            </label>

            {error && (
              <div className="flex items-start gap-2 bg-stamp-red-soft border border-stamp-red/30 text-stamp-red px-3 py-2.5 text-sm">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full h-[42px] bg-ink text-paper font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ink-soft transition-colors"
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-ink-soft mt-6">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-ink font-medium underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
