import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ScanLine,
  Search,
  RefreshCw,
  CheckCircle2,
  Loader2,
  FileWarning,
  ArrowRight,
} from "lucide-react";
import { getClaim } from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

const TERMINAL = ["completed", "failed", "error"];

export default function StatusPage() {
  const { claimId: routeClaimId } = useParams();
  const navigate = useNavigate();
  const [claimIdInput, setClaimIdInput] = useState(routeClaimId || "");
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(!!routeClaimId);
  const [error, setError] = useState("");
  const timerRef = useRef(null);

  const fetchClaim = async (id, silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    setError("");
    try {
      const res = await getClaim(id);
      setClaim(res.data);
    } catch (err) {
      setError(
        err?.response?.status === 404
          ? "No claim found with that ID."
          : err?.message || "Could not reach the backend."
      );
      setClaim(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!routeClaimId) return;
    fetchClaim(routeClaimId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeClaimId]);

  useEffect(() => {
    clearInterval(timerRef.current);
    if (claim && !TERMINAL.includes((claim.status || "").toLowerCase())) {
      timerRef.current = setInterval(() => {
        fetchClaim(routeClaimId, true);
      }, 3000);
    }
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claim?.status, routeClaimId]);

  const goToClaim = (e) => {
    e.preventDefault();
    if (claimIdInput.trim()) navigate(`/status/${claimIdInput.trim()}`);
  };

  const docs = claim?.documents || [];
  const completedDocs = docs.filter(
    (d) => (d.ocr_status || "").toLowerCase() === "completed"
  ).length;
  const totalDocs = claim?.document_count ?? docs.length;
  const pct = totalDocs ? Math.round((completedDocs / totalDocs) * 100) : 0;

  return (
    <div className="max-w-3xl mx-auto px-5 md:px-10 py-10 md:py-16">
      <header className="mb-8">
        <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-folder-dark mb-2">
          Intake — Step 02
        </p>
        <h1 className="font-display text-3xl md:text-4xl text-ink leading-tight">
          Watch the scan run
        </h1>
        <p className="text-ink-soft mt-2 text-sm max-w-lg">
          Track OCR and mapping progress for a claim, document by document.
        </p>
      </header>

      <form onSubmit={goToClaim} className="flex gap-2 mb-10">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft"
          />
          <input
            value={claimIdInput}
            onChange={(e) => setClaimIdInput(e.target.value)}
            placeholder="Paste a claim ID…"
            className="w-full border border-ink/20 bg-white pl-9 pr-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-folder-dark"
          />
        </div>
        <button
          type="submit"
          className="px-5 py-2.5 bg-ink text-paper text-sm font-medium hover:bg-ink-soft transition-colors"
        >
          Track
        </button>
      </form>

      {loading && (
        <div className="flex items-center gap-2 text-ink-soft text-sm">
          <Loader2 size={16} className="animate-spin" />
          Fetching claim…
        </div>
      )}

      {error && !loading && (
        <div className="flex items-center gap-2 bg-stamp-red-soft border border-stamp-red/30 text-stamp-red px-4 py-3 text-sm">
          <FileWarning size={16} />
          {error}
        </div>
      )}

      {claim && !loading && (
        <div className="space-y-8">
          <div className="border border-ink/15 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-mono text-ink-soft">
                  {claim.claim_id}
                </p>
                <p className="font-display text-xl text-ink mt-0.5">
                  {claim.file_no || "Untitled claim"}
                </p>
              </div>
              <StatusBadge status={claim.status} />
            </div>

            <div className="mt-5">
              <div className="flex justify-between text-xs font-mono text-ink-soft mb-1.5">
                <span>
                  {completedDocs} / {totalDocs} documents scanned
                </span>
                <span>{pct}%</span>
              </div>
              <div className="h-2 bg-ink/10 overflow-hidden relative">
                <div
                  className="h-full bg-folder-dark transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
                {pct < 100 && (
                  <div className="absolute inset-0 w-1/3 bg-white/40 animate-scan" />
                )}
              </div>
            </div>

            {claim.status?.toLowerCase() === "completed" && (
              <button
                onClick={() => navigate(`/claims/${claim.claim_id}`)}
                className="mt-5 flex items-center gap-1.5 text-sm font-medium text-ink hover:text-folder-dark transition-colors"
              >
                Review extracted documents <ArrowRight size={14} />
              </button>
            )}
          </div>

          <div>
            <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-3">
              Documents ({docs.length})
            </p>
            <div className="space-y-2">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 border border-ink/10 bg-white/70 px-4 py-3"
                >
                  {(doc.ocr_status || "").toLowerCase() === "completed" ? (
                    <CheckCircle2 size={17} className="text-verify-green shrink-0" />
                  ) : (
                    <Loader2 size={17} className="text-amber animate-spin shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-ink font-medium truncate">
                      {doc.document_type?.replace(/_/g, " ") || "unknown"}
                    </p>
                    <p className="text-xs text-ink-soft font-mono">
                      pages {doc.pages_processed?.join(", ") || "—"}
                    </p>
                  </div>
                  <StatusBadge status={doc.ocr_status} />
                  <StatusBadge status={doc.mapping_status} />
                </div>
              ))}
              {docs.length === 0 && (
                <p className="text-sm text-ink-soft italic">
                  No documents split out yet — check back shortly.
                </p>
              )}
            </div>
          </div>

          <button
            onClick={() => fetchClaim(routeClaimId)}
            className="flex items-center gap-1.5 text-xs font-mono text-ink-soft hover:text-ink"
          >
            <RefreshCw size={13} /> refresh now
          </button>
        </div>
      )}

      {!claim && !loading && !error && (
        <div className="flex flex-col items-center text-center py-16 border border-dashed border-ink/20 text-ink-soft">
          <ScanLine size={28} className="mb-3 text-folder-dark" />
          <p className="text-sm">
            Enter a claim ID above to watch its processing status.
          </p>
        </div>
      )}
    </div>
  );
}
