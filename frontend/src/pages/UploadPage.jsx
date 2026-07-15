import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileText, X, Loader2, AlertTriangle } from "lucide-react";
import { uploadClaim } from "../api/client.js";

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [fileNo, setFileNo] = useState("");
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }, []);

  const submit = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    setProgress(0);
    try {
      const res = await uploadClaim(file, fileNo, setProgress);
      const claimId = res.data?.claim_id;
      if (claimId) {
        navigate(`/status/${claimId}`);
      } else {
        setError("Upload succeeded but no claim_id was returned.");
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail
          ? typeof err.response.data.detail === "string"
            ? err.response.data.detail
            : "The backend rejected this file. Check the request payload."
          : err?.message || "Could not reach the backend."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-5 md:px-10 py-10 md:py-16">
      <header className="mb-10">
        <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-folder-dark mb-2">
          Intake — Step 01
        </p>
        <h1 className="font-display text-3xl md:text-4xl text-ink leading-tight">
          Drop the claim file on the desk
        </h1>
        <p className="text-ink-soft mt-2 text-sm max-w-lg">
          Upload the source PDF — bills, discharge summary, insurance form,
          bank statement, whatever's stapled together. The OCR engine will
          split it into documents and pull out the fields automatically.
        </p>
      </header>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative cursor-pointer border-2 border-dashed transition-colors px-6 py-14 flex flex-col items-center justify-center text-center ${
          dragging
            ? "border-folder-dark bg-folder/15"
            : "border-ink/25 bg-white/40 hover:border-ink/40"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        {!file ? (
          <>
            <div className="w-14 h-14 rounded-full bg-ink text-paper flex items-center justify-center mb-4 rotate-[-4deg]">
              <UploadCloud size={24} />
            </div>
            <p className="text-ink font-medium">
              Drag a PDF here, or click to browse
            </p>
            <p className="text-ink-soft text-xs mt-1 font-mono">
              single file · PDF only
            </p>
          </>
        ) : (
          <div className="flex items-center gap-3 bg-white border border-ink/15 px-4 py-3 max-w-full">
            <FileText size={22} className="text-folder-dark shrink-0" />
            <div className="text-left min-w-0">
              <p className="text-sm text-ink font-medium truncate max-w-[16rem]">
                {file.name}
              </p>
              <p className="text-xs text-ink-soft font-mono">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            {!uploading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="text-ink-soft hover:text-stamp-red ml-2"
              >
                <X size={16} />
              </button>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_auto] items-end">
        <label className="block">
          <span className="text-xs font-mono uppercase tracking-wide text-ink-soft">
            File / reference no.{" "}
            <span className="normal-case text-ink-soft/60">(optional)</span>
          </span>
          <input
            value={fileNo}
            onChange={(e) => setFileNo(e.target.value)}
            placeholder="e.g. 20251015B001RH03761"
            className="mt-1 w-full border border-ink/20 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-folder-dark"
          />
        </label>
        <button
          disabled={!file || uploading}
          onClick={submit}
          className="h-[42px] px-6 bg-ink text-paper font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ink-soft transition-colors"
        >
          {uploading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Uploading {progress}%
            </>
          ) : (
            "Submit claim"
          )}
        </button>
      </div>

      {uploading && (
        <div className="mt-3 h-1.5 w-full bg-ink/10 overflow-hidden">
          <div
            className="h-full bg-folder-dark transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {error && (
        <div className="mt-6 flex items-start gap-2 bg-stamp-red-soft border border-stamp-red/30 text-stamp-red px-4 py-3 text-sm">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="mt-14 grid sm:grid-cols-3 gap-4">
        {[
          {
            n: "01",
            t: "Split",
            d: "Multi-doc PDFs are separated into bills, forms, reports.",
          },
          {
            n: "02",
            t: "Extract",
            d: "Fields are pulled out as structured JSON, page by page.",
          },
          {
            n: "03",
            t: "Review",
            d: "Missing or wrong fields stay editable on the review desk.",
          },
        ].map((s) => (
          <div key={s.n} className="border-t-2 border-folder-dark pt-3">
            <p className="font-mono text-xs text-folder-dark">{s.n}</p>
            <p className="font-display text-lg text-ink mt-1">{s.t}</p>
            <p className="text-xs text-ink-soft mt-1 leading-relaxed">{s.d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
