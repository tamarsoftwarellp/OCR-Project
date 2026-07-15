const STYLES = {
  completed: "bg-verify-green-soft text-verify-green border-verify-green/30",
  approved: "bg-verify-green-soft text-verify-green border-verify-green/30",
  processing: "bg-amber-soft text-amber border-amber/30",
  pending: "bg-amber-soft text-amber border-amber/30",
  in_progress: "bg-amber-soft text-amber border-amber/30",
  failed: "bg-stamp-red-soft text-stamp-red border-stamp-red/30",
  rejected: "bg-stamp-red-soft text-stamp-red border-stamp-red/30",
  error: "bg-stamp-red-soft text-stamp-red border-stamp-red/30",
  default: "bg-ink/5 text-ink-soft border-ink/15",
};

export default function StatusBadge({ status, className = "" }) {
  const key = (status || "").toLowerCase();
  const style = STYLES[key] || STYLES.default;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 border text-[11px] font-mono uppercase tracking-wide ${style} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {status ? status.replace(/_/g, " ") : "unknown"}
    </span>
  );
}
