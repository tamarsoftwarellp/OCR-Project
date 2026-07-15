"""
Document-level endpoints.

"Document" here = ONE classified sub-document produced by the OCR engine
for a claim, e.g. "insurance_form", "discharge_summary", "invoice",
"bank_statement", "unknown". A single claim (one uploaded PDF) can and
usually does produce SEVERAL of these - including MULTIPLE of the same
document_type (Invoice 1, Invoice 2, Prescription 1, Prescription 2...).

Important design choices:
- We store the OCR engine's output AS-IS in MongoDB. We do NOT rename or
  normalize the dynamic OCR keys here - that belongs in a separate mapping
  layer, not this ingestion path.
- Uniqueness is (claim_id, source_file_name) - NOT (claim_id, document_type) -
  so a second invoice never overwrites the first one. `sequence` gives each
  document_type its own 1, 2, 3... ordering for the frontend to render
  "Invoice 1", "Invoice 2", etc.
- Reviewer-entered data (entity_verification, entity_remarks, review_status)
  lives in fields separate from the OCR output (all_extracted_entities,
  all_extracted_tables) and is never touched by re-ingestion of OCR data.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user, verify_ocr_callback_secret

from app.database import claims_collection, documents_collection
from app.models.schemas import (
    OcrDocumentIngestRequest,
    OcrDocumentBulkIngestRequest,
    OcrEngineCallbackRequest,
    DocumentOut,
    DocumentSummary,
    Warnings,
    EntityUpdateRequest,
    TablesUpdateRequest,
)
from app.utils import now_utc, to_object_id, serialize_doc

router = APIRouter(
    prefix="/claims/{claim_id}/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)

# The OCR engine callback is called by a machine (no user login), so it
# lives on its own router with its own auth (shared secret query param)
# instead of the user-JWT dependency above. See core/security.py::
# verify_ocr_callback_secret and claims.py::_build_callback_url.
callback_router = APIRouter(
    prefix="/claims/{claim_id}/documents",
    tags=["documents"],
    dependencies=[Depends(verify_ocr_callback_secret)],
)
logger = logging.getLogger(__name__)

_TRAILING_DIGITS_RE = re.compile(r"(\d+)(?=\.\w+$)")


async def _assert_claim_exists(claim_id: str):
    claim = await claims_collection.find_one({"_id": to_object_id(claim_id)})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def _derive_sequence_from_filename(file_name: Optional[str]) -> Optional[int]:
    """invoice_002.json -> 2. Falls back to None if the engine's filename
    doesn't carry a trailing number (normalized later)."""
    if not file_name:
        return None
    match = _TRAILING_DIGITS_RE.search(file_name)
    return int(match.group(1)) if match else None


def _document_out_from_record(doc: dict) -> DocumentOut:
    d = serialize_doc(doc)
    return DocumentOut(
        id=d["id"],
        document_id=d.get("document_id"),
        document_type=d["document_type"],
        source_file_name=d.get("source_file_name"),
        sequence=d.get("sequence"),
        pages_processed=d.get("pages_processed", []),
        global_metadata=d.get("global_metadata", {}),
        all_extracted_entities=d.get("all_extracted_entities", {}),
        all_extracted_tables=d.get("all_extracted_tables", []),
        warnings=Warnings(**d.get("warnings", {})),
        ocr_status=d.get("ocr_status"),
        raw_ocr_response=d.get("raw_ocr_response", {}),
        structured_ocr_data=d.get("structured_ocr_data", {}),
        mapped_fields=d.get("mapped_fields", {}),
        mapping_status=d.get("mapping_status"),
        error_message=d.get("error_message"),
        processed_page_count=d.get("processed_page_count"),
        total_page_count=d.get("total_page_count"),
        review_status=d.get("review_status", "pending"),
        entity_verification=d.get("entity_verification", {}),
        entity_remarks=d.get("entity_remarks", {}),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


def _document_summary_from_record(doc: dict) -> DocumentSummary:
    d = serialize_doc(doc)
    return DocumentSummary(
        id=d["id"],
        document_type=d["document_type"],
        source_file_name=d.get("source_file_name"),
        sequence=d.get("sequence"),
        pages_processed=d.get("pages_processed", []),
        ocr_status=d.get("ocr_status"),
        review_status=d.get("review_status", "pending"),
        error_message=d.get("error_message"),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


async def _upsert_document(claim_id: str, doc_record: dict, source_file_name: Optional[str]) -> dict:
    """Upsert keyed on (claim_id, source_file_name) when we have a filename -
    this is what actually makes multiple invoices/prescriptions/lab reports
    per claim work instead of overwriting each other. Falls back to
    (claim_id, document_type) only when the engine gave us no filename at all
    (legacy / direct ingest callers)."""
    if source_file_name:
        filter_query = {"claim_id": claim_id, "source_file_name": source_file_name}
    else:
        filter_query = {"claim_id": claim_id, "document_type": doc_record["document_type"]}

    result = await documents_collection.update_one(
        filter_query,
        {"$set": doc_record},
        upsert=True,
    )
    logger.info(
        "Upserted document claim=%s type=%s file=%s matched=%s modified=%s upserted_id=%s",
        claim_id,
        doc_record["document_type"],
        source_file_name,
        result.matched_count,
        result.modified_count,
        result.upserted_id,
    )
    updated = await documents_collection.find_one(filter_query)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to persist OCR document")
    return updated


async def _normalize_sequences(claim_id: str) -> None:
    """Backfill `sequence` for any document in this claim that doesn't have
    one yet (e.g. engine filenames without trailing digits), so the frontend
    can always render 'Invoice 1', 'Invoice 2', ... predictably. Idempotent -
    safe to call after every ingest."""
    cursor = documents_collection.find({"claim_id": claim_id}).sort("created_at", 1)
    by_type: dict = {}
    async for doc in cursor:
        by_type.setdefault(doc["document_type"], []).append(doc)

    for doc_type, docs in by_type.items():
        used = {d.get("sequence") for d in docs if isinstance(d.get("sequence"), int)}
        next_seq = 1
        for doc in docs:
            if isinstance(doc.get("sequence"), int):
                continue
            while next_seq in used:
                next_seq += 1
            used.add(next_seq)
            await documents_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"sequence": next_seq}},
            )


@router.get("", response_model=List[DocumentSummary])
async def list_documents(claim_id: str):
    """Lightweight listing so the frontend can render dynamic document
    tabs/cards WITHOUT hardcoding document types and without pulling the full
    OCR payload for every document up front."""
    await _assert_claim_exists(claim_id)
    cursor = documents_collection.find({"claim_id": claim_id}).sort(
        [("document_type", 1), ("sequence", 1)]
    )
    return [_document_summary_from_record(doc) async for doc in cursor]


@router.post("", response_model=DocumentOut, status_code=201)
async def ingest_ocr_document(claim_id: str, payload: OcrDocumentIngestRequest):
    """Called by the OCR engine (or the worker wrapping it) once ONE
    document_type has been fully extracted for this claim. Saves the JSON
    exactly as received."""
    await _assert_claim_exists(claim_id)

    now = now_utc()
    sequence = payload.sequence if payload.sequence is not None else _derive_sequence_from_filename(payload.source_file_name)
    doc_record = {
        "claim_id": claim_id,
        "document_type": payload.document_type,
        "source_file_name": payload.source_file_name,
        "sequence": sequence,
        "pages_processed": payload.pages_processed,
        "global_metadata": payload.global_metadata,
        "all_extracted_entities": payload.all_extracted_entities,
        "all_extracted_tables": payload.all_extracted_tables,
        "warnings": payload.warnings.model_dump(),
        "model": payload.model,
        "prompt_version": payload.prompt_version,
        "processed_at": payload.processed_at,
        "usage": payload.usage,
        "ocr_status": "processing",
        "status": "processing",
        "updated_at": now,
    }

    existing = await documents_collection.find_one(
        {"claim_id": claim_id, "source_file_name": payload.source_file_name}
        if payload.source_file_name
        else {"claim_id": claim_id, "document_type": payload.document_type}
    )
    if not existing:
        doc_record["created_at"] = now

    updated = await _upsert_document(claim_id, doc_record, payload.source_file_name)
    await _normalize_sequences(claim_id)
    updated = await documents_collection.find_one({"_id": updated["_id"]})

    await claims_collection.update_one(
        {"_id": to_object_id(claim_id)},
        {"$set": {"status": "processing", "updated_at": now}},
    )

    return _document_out_from_record(updated)


@router.post("/bulk", response_model=List[DocumentOut], status_code=201)
async def ingest_ocr_documents_bulk(claim_id: str, payload: OcrDocumentBulkIngestRequest):
    """Called once the engine has finished the ENTIRE claim - pushes every
    classified sub-document (all files under 09_llm_json/) in one shot."""
    results = []
    for single_doc in payload.documents:
        results.append(await ingest_ocr_document(claim_id, single_doc))

    result = await claims_collection.update_one(
        {"_id": to_object_id(claim_id)},
        {"$set": {"status": "completed", "updated_at": now_utc()}},
    )
    logger.info(
        "Marked claim=%s completed after bulk ingest matched=%s modified=%s",
        claim_id,
        result.matched_count,
        result.modified_count,
    )
    return results


def _extract_document_error(content: dict) -> Optional[str]:
    """Each llm_json artifact carries its OWN error info (from parsing that
    specific file), separate from the claim-wide `payload.error_message`
    (which is just the FIRST error found across ALL sub-documents). Using
    the claim-wide one on every row was contaminating clean documents
    (bank_statement, insurance_form...) with an error that only belonged to
    one broken document (e.g. invoice_001)."""
    collected: List[str] = []
    for key in ("errors", "llm_json_errors"):
        value = content.get(key)
        if isinstance(value, list):
            collected.extend(str(item) for item in value if item)
        elif value:
            collected.append(str(value))

    warnings_block = content.get("warnings")
    if isinstance(warnings_block, dict):
        value = warnings_block.get("errors")
        if isinstance(value, list):
            collected.extend(str(item) for item in value if item)
        elif value:
            collected.append(str(value))

    return collected[0] if collected else None


def _extract_llm_json_entries(payload: OcrEngineCallbackRequest) -> list:
    """The engine emits one clean per-document JSON per classified sub-document
    under structured_ocr_data.llm_json (and duplicated inside raw_ocr_response).
    Each entry looks like {"file_name": "invoice_001.json", "content": {...}}
    where `content` already matches the OcrDocumentIngestRequest shape
    (document_type, all_extracted_entities, all_extracted_tables, ...).
    We pull those out so each sub-document gets saved as its own row,
    exactly as the engine produced it - no merging, no flattening."""
    for source in (payload.structured_ocr_data, payload.raw_ocr_response):
        if isinstance(source, dict):
            entries = source.get("llm_json")
            if isinstance(entries, list) and entries:
                return entries
    return []


@callback_router.api_route("/callback", methods=["POST", "PATCH"], response_model=List[DocumentOut])
async def ingest_ocr_callback(claim_id: str, payload: OcrEngineCallbackRequest):
    """Dedicated callback endpoint for the OCR engine final payload.

    The engine finishes an entire claim in one go and may have classified it
    into several sub-documents (insurance_form, invoice, discharge_summary...),
    including MULTIPLE of the same document_type. Each classified file gets
    its OWN row in `documents_collection`, keyed on (claim_id,
    source_file_name) so re-runs update in place and distinct files never
    collide, saved exactly as the engine's per-document JSON."""
    await _assert_claim_exists(claim_id)

    if payload.claim_id and payload.claim_id != claim_id:
        raise HTTPException(status_code=400, detail="claim_id in path does not match payload")

    effective_status = (payload.ocr_status or payload.status or "completed").lower()
    if effective_status not in {"completed", "failed", "processing"}:
        raise HTTPException(status_code=400, detail="ocr_status must be completed, failed, or processing")

    now = payload.updated_at or now_utc()
    llm_json_entries = _extract_llm_json_entries(payload)

    saved_ids: List = []

    if llm_json_entries:
        for entry in llm_json_entries:
            content = entry.get("content") if isinstance(entry, dict) else None
            if not isinstance(content, dict):
                continue

            doc_type = content.get("document_type") or payload.document_type or "unknown"
            source_file_name = entry.get("file_name")
            warnings_raw = content.get("warnings")
            if not isinstance(warnings_raw, dict):
                warnings_raw = {}
            document_error_message = _extract_document_error(content)

            existing = await documents_collection.find_one(
                {"claim_id": claim_id, "source_file_name": source_file_name}
                if source_file_name
                else {"claim_id": claim_id, "document_type": doc_type}
            )

            doc_record = {
                "claim_id": claim_id,
                "document_id": payload.document_id,
                "document_type": doc_type,
                "source_file_name": source_file_name,
                "sequence": _derive_sequence_from_filename(source_file_name),
                "file_url": payload.file_url,
                "mime_type": payload.mime_type,
                "pdf_name": payload.pdf_name,
                "ocr_status": effective_status,
                "status": effective_status,
                "mapping_status": payload.mapping_status or effective_status,
                "error_message": document_error_message,
                "pages_processed": content.get("pages_processed", []),
                "processed_pages": payload.processed_pages,
                "processed_page_count": payload.processed_page_count,
                "total_page_count": payload.total_page_count,
                "global_metadata": content.get("global_metadata", {}),
                "all_extracted_entities": content.get("all_extracted_entities", {}),
                "all_extracted_tables": content.get("all_extracted_tables", []),
                "warnings": warnings_raw,
                "model": content.get("model"),
                "prompt_version": content.get("prompt_version"),
                "processed_at": content.get("processed_at"),
                "usage": content.get("usage"),
                "updated_at": now,
            }
            if not existing:
                doc_record["created_at"] = now

            updated = await _upsert_document(claim_id, doc_record, source_file_name)
            saved_ids.append(updated["_id"])
    else:
        document_type = payload.document_type or "claim_pdf"
        existing = await documents_collection.find_one(
            {"claim_id": claim_id, "document_type": document_type}
        )
        doc_record = {
            "claim_id": claim_id,
            "document_id": payload.document_id,
            "document_type": document_type,
            "file_url": payload.file_url,
            "mime_type": payload.mime_type,
            "ocr_status": effective_status,
            "status": effective_status,
            "raw_ocr_response": payload.raw_ocr_response,
            "structured_ocr_data": payload.structured_ocr_data,
            "mapped_fields": payload.mapped_fields,
            "mapping_status": payload.mapping_status or effective_status,
            "error_message": payload.error_message,
            "processed_pages": payload.processed_pages,
            "pages_processed": payload.processed_pages,
            "processed_page_count": payload.processed_page_count,
            "total_page_count": payload.total_page_count,
            "global_metadata": {},
            "all_extracted_entities": {},
            "all_extracted_tables": [],
            "warnings": {},
            "pdf_name": payload.pdf_name,
            "updated_at": now,
        }
        if not existing:
            doc_record["created_at"] = now

        updated = await _upsert_document(claim_id, doc_record, None)
        saved_ids.append(updated["_id"])

    await _normalize_sequences(claim_id)

    claim_status = "completed" if effective_status == "completed" else "failed" if effective_status == "failed" else "processing"
    claim_result = await claims_collection.update_one(
        {"_id": to_object_id(claim_id)},
        {"$set": {"status": claim_status, "updated_at": now}},
    )
    logger.info(
        "Claim status updated from callback claim=%s status=%s matched=%s modified=%s",
        claim_id,
        claim_status,
        claim_result.matched_count,
        claim_result.modified_count,
    )

    saved_docs = []
    for doc_id in saved_ids:
        updated = await documents_collection.find_one({"_id": doc_id})
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to persist OCR callback")
        saved_docs.append(_document_out_from_record(updated))

    return saved_docs


@router.get("/{document_type}", response_model=DocumentOut)
async def get_document(
    claim_id: str,
    document_type: str,
    source_file_name: Optional[str] = Query(default=None),
    sequence: Optional[int] = Query(default=None),
):
    """Fetch one document. If a claim has multiple documents of this
    document_type (Invoice 1, Invoice 2, ...), disambiguate with
    `source_file_name` or `sequence`; otherwise the most recently updated
    one of that type is returned."""
    query: dict = {"claim_id": claim_id, "document_type": document_type}
    if source_file_name:
        query["source_file_name"] = source_file_name
    elif sequence is not None:
        query["sequence"] = sequence

    doc = await documents_collection.find_one(query, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this claim")
    return _document_out_from_record(doc)


@router.patch("/{document_type}/entities", response_model=DocumentOut)
async def update_entity(
    claim_id: str,
    document_type: str,
    payload: EntityUpdateRequest,
    source_file_name: Optional[str] = Query(default=None),
    sequence: Optional[int] = Query(default=None),
):
    """Reviewer corrects / fills a single entity value in the review form.
    This is how manually-typed or corrected fields get persisted - it ONLY
    ever touches all_extracted_entities/entity_verification/entity_remarks,
    never the rest of the raw OCR payload, keeping OCR output and reviewer
    input strictly separate.

    If a claim has multiple documents of this document_type, disambiguate
    with `source_file_name` or `sequence`; otherwise the most recently
    updated one of that type is targeted."""
    query: dict = {"claim_id": claim_id, "document_type": document_type}
    if source_file_name:
        query["source_file_name"] = source_file_name
    elif sequence is not None:
        query["sequence"] = sequence

    doc = await documents_collection.find_one(query, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this claim")

    update_fields = {
        f"all_extracted_entities.{payload.key}": payload.value,
        "updated_at": now_utc(),
        "review_status": "in_review",
    }
    if payload.verified is not None:
        update_fields[f"entity_verification.{payload.key}"] = payload.verified
    if payload.remarks is not None:
        update_fields[f"entity_remarks.{payload.key}"] = payload.remarks

    updated = await documents_collection.find_one_and_update(
        {"_id": doc["_id"]},
        {"$set": update_fields},
        return_document=True,
    )
    return _document_out_from_record(updated)


@router.delete("/{document_type}/entities/{key}", response_model=DocumentOut)
async def delete_entity(
    claim_id: str,
    document_type: str,
    key: str,
    source_file_name: Optional[str] = Query(default=None),
    sequence: Optional[int] = Query(default=None),
):
    """Reviewer removes a field that shouldn't exist at all (e.g. the OCR
    engine hallucinated a key, or a manually-added field was a mistake).
    Uses $unset so the key disappears entirely rather than being set to an
    empty string - keeps `Extracted fields (N)` count honest."""
    query: dict = {"claim_id": claim_id, "document_type": document_type}
    if source_file_name:
        query["source_file_name"] = source_file_name
    elif sequence is not None:
        query["sequence"] = sequence

    doc = await documents_collection.find_one(query, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this claim")

    updated = await documents_collection.find_one_and_update(
        {"_id": doc["_id"]},
        {
            "$unset": {
                f"all_extracted_entities.{key}": "",
                f"entity_verification.{key}": "",
                f"entity_remarks.{key}": "",
            },
            "$set": {"updated_at": now_utc(), "review_status": "in_review"},
        },
        return_document=True,
    )
    return _document_out_from_record(updated)


@router.put("/{document_type}/tables", response_model=DocumentOut)
async def update_tables(
    claim_id: str,
    document_type: str,
    payload: TablesUpdateRequest,
    source_file_name: Optional[str] = Query(default=None),
    sequence: Optional[int] = Query(default=None),
):
    """Reviewer adds/edits/removes tables, rows, columns, or individual
    cells. Tables are dynamic in shape (headers differ per document), so
    rather than patching individual cells server-side we accept the WHOLE
    edited `all_extracted_tables` array from the frontend - which already
    holds the current, in-progress edited state - and persist it as-is.
    Same separation-of-concerns rule as entities: this only ever touches
    all_extracted_tables, never the rest of the raw OCR payload."""
    query: dict = {"claim_id": claim_id, "document_type": document_type}
    if source_file_name:
        query["source_file_name"] = source_file_name
    elif sequence is not None:
        query["sequence"] = sequence

    doc = await documents_collection.find_one(query, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this claim")

    updated = await documents_collection.find_one_and_update(
        {"_id": doc["_id"]},
        {
            "$set": {
                "all_extracted_tables": payload.tables,
                "updated_at": now_utc(),
                "review_status": "in_review",
            }
        },
        return_document=True,
    )
    return _document_out_from_record(updated)