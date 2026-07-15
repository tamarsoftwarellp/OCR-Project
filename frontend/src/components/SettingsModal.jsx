import { useState } from "react";
import { X, CheckCircle2, XCircle } from "lucide-react";
import { getBaseUrl, setBaseUrl, checkHealth } from "../api/client.js";

export default function SettingsModal({ onClose }) {
  const [url, setUrl] = useState(getBaseUrl());
  const [status, setStatus] = useState(null); // null | "ok" | "fail" | "checking"

  const save = () => {
    setBaseUrl(url || "http://localhost:8000");
    onClose();
  };

  const test = async () => {
    setBaseUrl(url);
    setStatus("checking");
    try {
      await checkHealth();
      setStatus("ok");
    } catch {
      setStatus("fail");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm px-4">
      <div className="w-full max-w-md bg-paper border border-ink/15 shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-ink/10">
          <h3 className="font-display text-lg text-ink">API Endpoint</h3>
          <button onClick={onClose} className="text-ink-soft hover:text-ink">
            <X size={18} />
          </button>
        </div>
        <div className="p-5 space-y-3">
          <p className="text-xs text-ink-soft leading-relaxed">
            Point this desk at your Claim OCR Backend base URL (e.g. the host
            serving <code className="font-mono">/openapi.json</code>).
          </p>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-api.example.com"
            className="w-full border border-ink/20 bg-white px-3 py-2 text-sm font-mono text-ink focus:outline-none focus:ring-2 focus:ring-folder-dark"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={test}
              className="text-xs font-medium px-3 py-1.5 border border-ink/20 text-ink-soft hover:text-ink hover:border-ink/40 transition-colors"
            >
              Test connection
            </button>
            {status === "checking" && (
              <span className="text-xs text-ink-soft font-mono">checking…</span>
            )}
            {status === "ok" && (
              <span className="flex items-center gap-1 text-xs text-verify-green font-mono">
                <CheckCircle2 size={14} /> reachable
              </span>
            )}
            {status === "fail" && (
              <span className="flex items-center gap-1 text-xs text-stamp-red font-mono">
                <XCircle size={14} /> unreachable
              </span>
            )}
          </div>
        </div>
        <div className="px-5 py-4 border-t border-ink/10 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-ink-soft hover:text-ink"
          >
            Cancel
          </button>
          <button
            onClick={save}
            className="px-4 py-2 text-sm font-medium bg-ink text-paper hover:bg-ink-soft transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
