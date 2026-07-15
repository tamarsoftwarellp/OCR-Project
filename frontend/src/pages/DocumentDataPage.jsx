import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Loader2,
  FileWarning,
  Save,
  Table2,
  AlertTriangle,
  ChevronLeft,
  Check,
  CircleDot,
  Trash2,
  Plus,
  X,
} from "lucide-react";
import {
  getClaim,
  updateEntities,
  deleteEntity,
  updateTables,
  updateClaimStatus,
} from "../api/client.js";
import StatusBadge from "../components/StatusBadge.jsx";

function titleCase(s) {
  return (s || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function DocumentDataPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeType, setActiveType] = useState(null);
  const [edited, setEdited] = useState({}); // documentType -> {field: value}
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [statusSaving, setStatusSaving] = useState(false);
  const [newFieldKey, setNewFieldKey] = useState("");
  const [newFieldValue, setNewFieldValue] = useState("");
  const [deletingField, setDeletingField] = useState(null);
  const [editedTables, setEditedTables] = useState({}); // documentType -> tables array
  const [tablesSaving, setTablesSaving] = useState(false);
  const [tablesSaved, setTablesSaved] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getClaim(claimId);
      setClaim(res.data);
      const first = res.data?.documents?.[0]?.document_type;
      setActiveType((prev) => prev || first || null);
    } catch (err) {
      setError(
        err?.response?.status === 404
          ? "No claim found with that ID."
          : err?.message || "Could not reach the backend."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claimId]);

  const docs = claim?.documents || [];
  const activeDoc = useMemo(
    () => docs.find((d) => d.document_type === activeType),
    [docs, activeType]
  );

  const fieldsForActive = edited[activeType] || {};

  const setField = (docType, field, value) => {
    setSaved(false);
    setEdited((prev) => ({
      ...prev,
      [docType]: { ...(prev[docType] || {}), [field]: value },
    }));
  };

  const hasChanges = Object.keys(fieldsForActive).length > 0;

  const entities = activeDoc?.all_extracted_entities || {};
  // Union of saved fields + any newly-added/edited fields that haven't been
  // saved yet, so a freshly-added field shows up immediately without a
  // round-trip to the backend.
  const displayEntities = { ...entities, ...fieldsForActive };
  const totalFields = Object.keys(displayEntities).length;
  const missingCount = Object.values(displayEntities).filter(
    (v) => !v || String(v).toLowerCase() === "not available"
  ).length;

  const addEntityField = () => {
    const key = newFieldKey.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key || !activeDoc) return;
    if (key in displayEntities) {
      alert("A field with this name already exists.");
      return;
    }
    setField(activeDoc.document_type, key, newFieldValue);
    setNewFieldKey("");
    setNewFieldValue("");
  };

  const removeEntityField = async (field) => {
    if (!activeDoc) return;
    if (!window.confirm(`Remove field "${titleCase(field)}"? This can't be undone.`)) return;

    // Newly-added, not-yet-saved field: just drop it locally, no API call.
    if (!(field in entities)) {
      setEdited((prev) => {
        const next = { ...(prev[activeDoc.document_type] || {}) };
        delete next[field];
        return { ...prev, [activeDoc.document_type]: next };
      });
      return;
    }

    setDeletingField(field);
    try {
      await deleteEntity(claimId, activeDoc.document_type, field);
      setClaim((prev) => ({
        ...prev,
        documents: prev.documents.map((d) => {
          if (d.document_type !== activeDoc.document_type) return d;
          const nextEntities = { ...d.all_extracted_entities };
          delete nextEntities[field];
          return { ...d, all_extracted_entities: nextEntities };
        }),
      }));
      setEdited((prev) => {
        const next = { ...(prev[activeDoc.document_type] || {}) };
        delete next[field];
        return { ...prev, [activeDoc.document_type]: next };
      });
    } catch (err) {
      alert(err?.message || "Could not remove field.");
    } finally {
      setDeletingField(null);
    }
  };

  // ---- Tables: read/edit helpers ----
  const savedTables = activeDoc?.all_extracted_tables || [];
  const tablesForActive = editedTables[activeType] ?? savedTables;
  const tablesDirty = editedTables[activeType] !== undefined;

  const normalizedTable = (tbl) => ({
    ...tbl,
    headers: tbl.headers || (tbl.rows?.[0] ? Object.keys(tbl.rows[0]) : []),
    rows: tbl.rows || [],
  });

  const mutateTables = (mutator) => {
    if (!activeType) return;
    const base = (editedTables[activeType] ?? savedTables).map(normalizedTable);
    const next = mutator(base.map((t) => ({ ...t, rows: t.rows.map((r) => ({ ...r })) })));
    setEditedTables((prev) => ({ ...prev, [activeType]: next }));
    setTablesSaved(false);
  };

  const updateCell = (tableIndex, rowIndex, header, value) => {
    mutateTables((tables) => {
      tables[tableIndex].rows[rowIndex][header] = value;
      return tables;
    });
  };

  const addRow = (tableIndex) => {
    mutateTables((tables) => {
      const blankRow = {};
      tables[tableIndex].headers.forEach((h) => (blankRow[h] = ""));
      tables[tableIndex].rows.push(blankRow);
      return tables;
    });
  };

  const deleteRow = (tableIndex, rowIndex) => {
    mutateTables((tables) => {
      tables[tableIndex].rows.splice(rowIndex, 1);
      return tables;
    });
  };

  const addColumn = (tableIndex) => {
    const name = window.prompt("New column name:");
    if (!name) return;
    const key = name.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key) return;
    mutateTables((tables) => {
      if (!tables[tableIndex].headers.includes(key)) {
        tables[tableIndex].headers.push(key);
      }
      tables[tableIndex].rows.forEach((r) => {
        if (!(key in r)) r[key] = "";
      });
      return tables;
    });
  };

  const deleteColumn = (tableIndex, header) => {
    mutateTables((tables) => {
      tables[tableIndex].headers = tables[tableIndex].headers.filter((h) => h !== header);
      tables[tableIndex].rows.forEach((r) => delete r[header]);
      return tables;
    });
  };

  const deleteTable = (tableIndex) => {
    if (!window.confirm("Remove this entire table? This can't be undone.")) return;
    mutateTables((tables) => {
      tables.splice(tableIndex, 1);
      return tables;
    });
  };

  const addTable = () => {
    const name = window.prompt("New table name:", "New Table");
    if (!name) return;
    const headersRaw = window.prompt(
      "Column names, comma-separated (e.g. item, quantity, amount):",
      "column_1"
    );
    if (!headersRaw) return;
    const headers = headersRaw
      .split(",")
      .map((h) => h.trim().toLowerCase().replace(/\s+/g, "_"))
      .filter(Boolean);
    if (headers.length === 0) return;
    mutateTables((tables) => {
      tables.push({ table_name: name, headers, rows: [] });
      return tables;
    });
  };

  const saveTables = async () => {
    if (!activeDoc || !tablesDirty) return;
    setTablesSaving(true);
    try {
      const payloadTables = tablesForActive;
      await updateTables(claimId, activeDoc.document_type, payloadTables);
      setClaim((prev) => ({
        ...prev,
        documents: prev.documents.map((d) =>
          d.document_type === activeDoc.document_type
            ? { ...d, all_extracted_tables: payloadTables }
            : d
        ),
      }));
      setEditedTables((prev) => {
        const next = { ...prev };
        delete next[activeType];
        return next;
      });
      setTablesSaved(true);
      setTimeout(() => setTablesSaved(false), 2500);
    } catch (err) {
      alert(err?.message || "Could not save table changes.");
    } finally {
      setTablesSaving(false);
    }
  };

  const saveEntities = async () => {
    if (!activeDoc || !hasChanges) return;
    setSaving(true);
    try {
      await updateEntities(claimId, activeDoc.document_type, fieldsForActive);
      setClaim((prev) => ({
        ...prev,
        documents: prev.documents.map((d) =>
          d.document_type === activeDoc.document_type
            ? {
                ...d,
                all_extracted_entities: {
                  ...d.all_extracted_entities,
                  ...fieldsForActive,
                },
              }
            : d
        ),
      }));
      setEdited((prev) => ({ ...prev, [activeDoc.document_type]: {} }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      let message = err?.message || "Could not save changes.";
      if (Array.isArray(detail)) {
        message = detail.map((d) => d.msg).filter(Boolean).join("; ") || message;
      } else if (typeof detail === "string") {
        message = detail;
      }
      alert(message);
    } finally {
      setSaving(false);
    }
  };

  const changeClaimStatus = async (status) => {
    setStatusSaving(true);
    try {
      await updateClaimStatus(claimId, status);
      setClaim((prev) => ({ ...prev, status }));
    } catch (err) {
      alert(err?.message || "Could not update claim status.");
    } finally {
      setStatusSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-5 md:px-10 py-16 flex items-center gap-2 text-ink-soft text-sm">
        <Loader2 size={16} className="animate-spin" />
        Opening case file…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-5 md:px-10 py-16">
        <div className="flex items-center gap-2 bg-stamp-red-soft border border-stamp-red/30 text-stamp-red px-4 py-3 text-sm">
          <FileWarning size={16} />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-5 md:px-10 py-8 md:py-12">
      <button
        onClick={() => navigate("/claims")}
        className="flex items-center gap-1 text-xs font-mono text-ink-soft hover:text-ink mb-6"
      >
        <ChevronLeft size={13} /> case register
      </button>

      <header className="mb-8 flex flex-wrap items-start justify-between gap-4 pb-6 border-b border-ink/10">
        <div className="min-w-0">
          <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-folder-dark mb-2">
            Step 04 · Document-wise data
          </p>
          <h1 className="font-display text-3xl md:text-4xl text-ink leading-tight truncate">
            {claim?.file_no || "Untitled claim"}
          </h1>
          <p className="text-ink-soft mt-2 text-xs font-mono">
            {claim?.claim_id}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={claim?.status} />
          <select
            disabled={statusSaving}
            value=""
            onChange={(e) => e.target.value && changeClaimStatus(e.target.value)}
            className="text-xs font-mono border border-ink/20 bg-white px-2.5 py-2 focus:outline-none focus:ring-2 focus:ring-folder-dark cursor-pointer"
          >
            <option value="">Update status…</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </header>

      {docs.length === 0 ? (
        <div className="flex flex-col items-center text-center py-16 border border-dashed border-ink/20 text-ink-soft">
          <p className="text-sm">
            No documents have been extracted for this claim yet.
          </p>
        </div>
      ) : (
        <div className="lg:flex lg:items-start lg:gap-8">
          {/* Folder tabs */}
          <div className="lg:w-60 shrink-0 mb-6 lg:mb-0 lg:sticky lg:top-8">
            <p className="text-[10px] font-mono uppercase tracking-wide text-ink-soft/70 mb-2 px-1 hidden lg:block">
              {docs.length} document{docs.length !== 1 ? "s" : ""}
            </p>
            <div className="flex lg:flex-col gap-1.5 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0 scroll-thin">
              {docs.map((d, i) => {
                const isActive = activeType === d.document_type;
                const isEdited =
                  edited[d.document_type] &&
                  Object.keys(edited[d.document_type]).length > 0;
                return (
                  <button
                    key={d.id || i}
                    onClick={() => setActiveType(d.document_type)}
                    className={`shrink-0 text-left px-3.5 py-2.5 whitespace-nowrap lg:whitespace-normal border-l-[3px] transition-colors ${
                      isActive
                        ? "bg-ink text-paper border-folder-dark"
                        : "bg-white/70 text-ink-soft hover:bg-folder/15 hover:text-ink border-transparent"
                    }`}
                  >
                    <span className="text-sm font-medium flex items-center gap-1.5">
                      {titleCase(d.document_type)}
                      {isEdited && (
                        <CircleDot
                          size={10}
                          className={isActive ? "text-folder" : "text-folder-dark"}
                        />
                      )}
                    </span>
                    <span className="text-[10px] font-mono opacity-70 block mt-0.5">
                      {(d.ocr_status || "?").toUpperCase()}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active document detail */}
          {activeDoc && (
            <div className="flex-1 min-w-0 space-y-6">
              <div className="sticky top-14 md:top-0 z-10 -mx-5 md:-mx-10 lg:mx-0 px-5 md:px-10 lg:px-0 py-3.5 bg-paper/95 backdrop-blur-sm flex flex-wrap items-center justify-between gap-3 border-b border-ink/15">
                <div className="min-w-0">
                  <h2 className="font-display text-xl text-ink truncate">
                    {titleCase(activeDoc.document_type)}
                  </h2>
                  <p className="text-xs text-ink-soft font-mono mt-0.5 truncate">
                    {activeDoc.source_file_name} · pages{" "}
                    {activeDoc.pages_processed?.join(", ") || "—"}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={activeDoc.review_status} />
                  <button
                    onClick={saveEntities}
                    disabled={!hasChanges || saving}
                    className="flex items-center gap-1.5 px-4 py-2 bg-ink text-paper text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ink-soft transition-colors"
                  >
                    {saving ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : saved ? (
                      <Check size={14} />
                    ) : (
                      <Save size={14} />
                    )}
                    {saved ? "Saved" : hasChanges ? `Save ${Object.keys(fieldsForActive).length} change${Object.keys(fieldsForActive).length !== 1 ? "s" : ""}` : "Save changes"}
                  </button>
                </div>
              </div>

              {/* Warnings */}
              {(activeDoc.warnings?.ignored_handwritten_content?.length > 0 ||
                activeDoc.warnings?.unmapped_ambiguous_text_regions?.length >
                  0) && (
                <div className="flex items-start gap-2 bg-amber-soft border border-amber/30 text-amber px-4 py-3 text-xs">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    {activeDoc.warnings.ignored_handwritten_content?.length >
                      0 && (
                      <p>
                        {activeDoc.warnings.ignored_handwritten_content.length}{" "}
                        handwritten region(s) were ignored.
                      </p>
                    )}
                    {activeDoc.warnings.unmapped_ambiguous_text_regions
                      ?.length > 0 && (
                      <p>
                        {
                          activeDoc.warnings.unmapped_ambiguous_text_regions
                            .length
                        }{" "}
                        ambiguous region(s) could not be mapped.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Entities form */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-mono uppercase tracking-wide text-ink-soft">
                    Extracted fields ({totalFields})
                  </p>
                  {missingCount > 0 && (
                    <p className="text-xs font-mono text-stamp-red flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-stamp-red" />
                      {missingCount} missing
                    </p>
                  )}
                </div>
                <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-x-6 gap-y-5 bg-white border border-ink/15 p-5 md:p-6">
                  {Object.entries(displayEntities).map(([field, value]) => {
                    const current =
                      fieldsForActive[field] !== undefined
                        ? fieldsForActive[field]
                        : value;
                    const isMissing =
                      !value || String(value).toLowerCase() === "not available";
                    const isDirty = fieldsForActive[field] !== undefined;
                    const isNew = !(field in entities);
                    return (
                      <div key={field} className="block">
                        <span className="text-[11px] font-mono uppercase tracking-wide text-ink-soft/80 flex items-center gap-1.5 mb-1">
                          <span className="truncate">{titleCase(field)}</span>
                          {isNew ? (
                            <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-emerald-500" title="new field" />
                          ) : (
                            isDirty && (
                              <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-folder-dark" title="edited" />
                            )
                          )}
                          <button
                            type="button"
                            onClick={() => removeEntityField(field)}
                            disabled={deletingField === field}
                            title="Remove field"
                            className="ml-auto shrink-0 text-ink-soft/50 hover:text-stamp-red disabled:opacity-40"
                          >
                            {deletingField === field ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : (
                              <Trash2 size={12} />
                            )}
                          </button>
                        </span>
                        <input
                          value={current ?? ""}
                          onChange={(e) =>
                            setField(activeDoc.document_type, field, e.target.value)
                          }
                          placeholder={isMissing ? "Not extracted — enter manually" : ""}
                          className={`w-full border px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-folder-dark placeholder:text-stamp-red/50 placeholder:text-xs ${
                            isDirty
                              ? "border-folder-dark bg-folder/10"
                              : isMissing
                              ? "border-stamp-red/30 border-l-2 bg-white"
                              : "border-ink/15 bg-white"
                          }`}
                        />
                      </div>
                    );
                  })}
                  {totalFields === 0 && (
                    <p className="text-sm text-ink-soft italic sm:col-span-2 xl:col-span-3">
                      No fields were extracted for this document.
                    </p>
                  )}

                  {/* Add a new field the OCR engine didn't extract */}
                  <div className="sm:col-span-2 xl:col-span-3 flex flex-wrap items-end gap-2 pt-2 border-t border-ink/10 mt-1">
                    <label className="block">
                      <span className="text-[11px] font-mono uppercase tracking-wide text-ink-soft/80 block mb-1">
                        Field name
                      </span>
                      <input
                        value={newFieldKey}
                        onChange={(e) => setNewFieldKey(e.target.value)}
                        placeholder="e.g. discount_amount"
                        className="border border-ink/15 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-folder-dark w-48"
                      />
                    </label>
                    <label className="block flex-1 min-w-[160px]">
                      <span className="text-[11px] font-mono uppercase tracking-wide text-ink-soft/80 block mb-1">
                        Value
                      </span>
                      <input
                        value={newFieldValue}
                        onChange={(e) => setNewFieldValue(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && addEntityField()}
                        className="border border-ink/15 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-folder-dark w-full"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={addEntityField}
                      disabled={!newFieldKey.trim()}
                      className="flex items-center gap-1.5 px-3 py-2 border border-ink/20 text-sm font-medium hover:bg-paper-dim disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Plus size={14} /> Add field
                    </button>
                  </div>
                </div>
              </div>

              {/* Tables */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-mono uppercase tracking-wide text-ink-soft flex items-center gap-1.5">
                    <Table2 size={13} />
                    Extracted tables ({tablesForActive.length})
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={addTable}
                      className="flex items-center gap-1.5 px-3 py-1.5 border border-ink/20 text-xs font-medium hover:bg-paper-dim"
                    >
                      <Plus size={13} /> Add table
                    </button>
                    <button
                      type="button"
                      onClick={saveTables}
                      disabled={!tablesDirty || tablesSaving}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-ink text-paper text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ink-soft transition-colors"
                    >
                      {tablesSaving ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : tablesSaved ? (
                        <Check size={13} />
                      ) : (
                        <Save size={13} />
                      )}
                      {tablesSaved ? "Saved" : "Save tables"}
                    </button>
                  </div>
                </div>

                {tablesForActive.length === 0 ? (
                  <p className="text-sm text-ink-soft italic bg-white border border-ink/15 p-5">
                    No tables extracted for this document. Use "Add table" to create one manually.
                  </p>
                ) : (
                  <div className="space-y-6">
                    {tablesForActive.map((tbl, ti) => {
                      const headers =
                        tbl.headers ||
                        (tbl.rows?.[0] ? Object.keys(tbl.rows[0]) : []);
                      return (
                        <div key={ti} className="border border-ink/15 bg-white">
                          <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-ink/10 bg-paper-dim/60">
                            <p className="text-sm font-medium text-ink truncate">
                              {tbl.table_name ||
                                tbl.table_name_or_purpose ||
                                `Table ${ti + 1}`}
                            </p>
                            <div className="flex items-center gap-3 shrink-0">
                              <button
                                type="button"
                                onClick={() => addColumn(ti)}
                                className="text-[11px] font-mono uppercase text-ink-soft hover:text-ink flex items-center gap-1"
                                title="Add column"
                              >
                                <Plus size={12} /> column
                              </button>
                              <button
                                type="button"
                                onClick={() => addRow(ti)}
                                className="text-[11px] font-mono uppercase text-ink-soft hover:text-ink flex items-center gap-1"
                                title="Add row"
                              >
                                <Plus size={12} /> row
                              </button>
                              <button
                                type="button"
                                onClick={() => deleteTable(ti)}
                                className="text-ink-soft/60 hover:text-stamp-red"
                                title="Remove table"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>
                          <div className="overflow-x-auto scroll-thin">
                            <table className="w-full text-xs min-w-[560px]">
                              <thead>
                                <tr className="bg-paper-dim">
                                  {headers.map((h) => (
                                    <th
                                      key={h}
                                      className="text-left px-3 py-2 font-mono uppercase tracking-wide text-ink-soft whitespace-nowrap"
                                    >
                                      <span className="inline-flex items-center gap-1.5">
                                        {titleCase(h)}
                                        <button
                                          type="button"
                                          onClick={() => deleteColumn(ti, h)}
                                          title="Remove column"
                                          className="text-ink-soft/40 hover:text-stamp-red normal-case"
                                        >
                                          <X size={11} />
                                        </button>
                                      </span>
                                    </th>
                                  ))}
                                  <th className="w-8" />
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-ink/10">
                                {(tbl.rows || []).map((row, ri) => (
                                  <tr key={ri} className="even:bg-paper/40">
                                    {headers.map((h) => (
                                      <td key={h} className="px-1.5 py-1.5 text-ink align-top">
                                        <input
                                          value={row[h] ?? ""}
                                          onChange={(e) => updateCell(ti, ri, h, e.target.value)}
                                          className="w-full min-w-[90px] border border-transparent hover:border-ink/15 focus:border-folder-dark bg-transparent px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-folder-dark"
                                        />
                                      </td>
                                    ))}
                                    <td className="px-1.5 py-1.5 align-top">
                                      <button
                                        type="button"
                                        onClick={() => deleteRow(ti, ri)}
                                        title="Remove row"
                                        className="text-ink-soft/40 hover:text-stamp-red"
                                      >
                                        <Trash2 size={12} />
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                                {(tbl.rows || []).length === 0 && (
                                  <tr>
                                    <td
                                      colSpan={headers.length + 1}
                                      className="px-3 py-3 text-ink-soft italic"
                                    >
                                      No rows yet — use "row" above to add one.
                                    </td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              {tablesDirty && (
                <p className="text-[11px] font-mono text-folder-dark -mt-4">
                  Unsaved table changes — click "Save tables" to persist them.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}