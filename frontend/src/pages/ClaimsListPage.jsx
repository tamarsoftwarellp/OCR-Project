import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Loader2,
  FileWarning,
  ArrowUpRight,
  Trash2,
  FolderOpen,
} from "lucide-react";
import { listClaims, deleteClaim } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function ClaimsListPage() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deletingId, setDeletingId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listClaims();
      const data = Array.isArray(res.data)
        ? res.data
        : res.data?.claims || res.data?.items || [];
      setClaims(data);
    } catch (err) {
      setError(err?.message || "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const statuses = useMemo(() => {
    const s = new Set(claims.map((c) => (c.status || "unknown").toLowerCase()));
    return ["all", ...Array.from(s)];
  }, [claims]);

  const filtered = claims.filter((c) => {
    const matchesStatus =
      statusFilter === "all" ||
      (c.status || "unknown").toLowerCase() === statusFilter;
    const q = query.trim().toLowerCase();
    const matchesQuery =
      !q ||
      c.claim_id?.toLowerCase().includes(q) ||
      c.file_no?.toLowerCase().includes(q);
    return matchesStatus && matchesQuery;
  });

  const onDelete = async (e, claimId) => {
    e.stopPropagation();
    if (!confirm(`Delete claim ${claimId}? This cannot be undone.`)) return;
    setDeletingId(claimId);
    try {
      await deleteClaim(claimId);
      setClaims((prev) => prev.filter((c) => c.claim_id !== claimId));
    } catch (err) {
      alert(err?.message || "Could not delete claim.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-5 md:px-10 py-10 md:py-16">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-folder-dark mb-2">
            Step 03
          </p>
          <h1 className="font-display text-3xl md:text-4xl text-ink leading-tight">
            Case register
          </h1>
          <p className="text-ink-soft mt-2 text-sm max-w-lg">
            Every claim on file, its scan status, and how many documents came
            out of it.
          </p>
        </div>
        <div className="text-right font-mono text-xs text-ink-soft">
          {!loading && `${filtered.length} of ${claims.length} claims`}
        </div>
      </header>

      <div className="flex flex-wrap gap-2 mb-6">
        <div className="relative flex-1 min-w-[220px]">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search claim ID or file no…"
            className="w-full border border-ink/20 bg-white pl-9 pr-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-folder-dark"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wide border transition-colors ${
                statusFilter === s
                  ? "bg-ink text-paper border-ink"
                  : "border-ink/20 text-ink-soft hover:border-ink/40"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-ink-soft text-sm py-10">
          <Loader2 size={16} className="animate-spin" />
          Loading case register…
        </div>
      )}

      {error && !loading && (
        <div className="flex items-center gap-2 bg-stamp-red-soft border border-stamp-red/30 text-stamp-red px-4 py-3 text-sm">
          <FileWarning size={16} />
          {error}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center text-center py-16 border border-dashed border-ink/20 text-ink-soft">
          <FolderOpen size={28} className="mb-3 text-folder-dark" />
          <p className="text-sm">No claims match this filter yet.</p>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="border border-ink/15 bg-white divide-y divide-ink/10">
          {/* header row - desktop only */}
          <div className="hidden md:grid grid-cols-[1fr_1fr_100px_140px_110px_56px] gap-4 px-4 py-2.5 text-[10px] font-mono uppercase tracking-wide text-ink-soft bg-paper-dim">
            <span>Claim ID</span>
            <span>File No.</span>
            <span>Documents</span>
            <span>Status</span>
            <span>Created</span>
            <span />
          </div>
          {filtered.map((c) => (
            <div
              key={c.claim_id}
              onClick={() => navigate(`/claims/${c.claim_id}`)}
              className="grid grid-cols-2 md:grid-cols-[1fr_1fr_100px_140px_110px_56px] gap-4 px-4 py-3.5 items-center text-sm cursor-pointer hover:bg-folder/10 transition-colors"
            >
              <span className="font-mono text-xs text-ink truncate col-span-2 md:col-span-1">
                {c.claim_id}
              </span>
              <span className="text-ink-soft truncate">
                {c.file_no || <em className="not-italic text-ink-soft/50">—</em>}
              </span>
              <span className="font-mono text-xs text-ink-soft whitespace-nowrap">
                {c.document_count ?? "—"} docs
              </span>
              <span className="whitespace-nowrap">
                <StatusBadge status={c.status} />
              </span>
              <span className="text-xs text-ink-soft font-mono whitespace-nowrap">
                {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
              </span>
              <div className="flex justify-end gap-3">
                <button
                  onClick={(e) => onDelete(e, c.claim_id)}
                  disabled={deletingId === c.claim_id}
                  className="text-ink-soft hover:text-stamp-red transition-colors"
                  title="Delete claim"
                >
                  {deletingId === c.claim_id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
                <ArrowUpRight size={14} className="text-ink-soft" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
