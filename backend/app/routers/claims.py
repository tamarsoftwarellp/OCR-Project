"""
Claim-level endpoints.

Typical flow:
1. Frontend uploads the file directly to Cloudinary (client-side upload).
2. Frontend calls POST /claims with the Cloudinary URL -> we create a claim
   record with status="uploaded" and return claim_id.
3. Frontend (or a backend hook) triggers the OCR engine, passing claim_id +
   source_file_url. The engine works asynchronously.
4. As the OCR engine finishes each classified sub-document (insurance_form,
   invoice, discharge_summary, ...), it POSTs the raw JSON to
   /claims/{claim_id}/documents (see documents.py router) - saved AS-IS.
5. Frontend polls / fetches GET /claims/{claim_id} to render the review form,
   auto-filling whatever entities exist and leaving the rest blank for the
   reviewer to fill manually.
"""
from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from typing import List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode, urljoin

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pymongo import DESCENDING

from app.config import settings
from app.core.security import get_current_user
from app.database import claims_collection, documents_collection
from app.models.schemas import (
    ClaimCreateRequest,
    ClaimResponse,
    ClaimDetailResponse,
    DocumentOut,
    OcrEngineDispatchRequest,
    Warnings,
)
from app.services.cloudinary_service import upload_pdf_to_cloudinary
from app.utils import now_utc, serialize_doc, to_object_id

router = APIRouter(
    prefix="/claims", tags=["claims"], dependencies=[Depends(get_current_user)]
)
logger = logging.getLogger(__name__)
DEFAULT_DOCUMENT_TYPE = "claim_pdf"
ENGINE_PROCESS_PATH = "/ocr/process"


def _build_engine_dispatch_url() -> str:
    return urljoin(settings.OCR_ENGINE_URL.rstrip("/") + "/", ENGINE_PROCESS_PATH.lstrip("/"))


def _build_callback_url(claim_id: str) -> str:
    base = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/claims/{claim_id}/documents/callback"
    # Engine has no user login, so it authenticates via a shared secret
    # query param instead of a Bearer JWT - see core/security.py::
    # verify_ocr_callback_secret.
    query = urlencode({"key": settings.OCR_CALLBACK_SECRET})
    return f"{base}?{query}"


def _normalize_document_type(document_type: Optional[str]) -> str:
    return document_type or DEFAULT_DOCUMENT_TYPE


def _guess_mime_type(source_file_url: str, fallback_mime_type: Optional[str] = None) -> str:
    if fallback_mime_type:
        return fallback_mime_type
    guessed, _ = mimetypes.guess_type(source_file_url or "")
    return guessed or "application/octet-stream"


def _post_json(url: str, payload: dict, timeout: int = 60) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=timeout) as response:
        response_text = response.read().decode("utf-8", errors="ignore")
        return response.status, response_text


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


# ---------------------------------------------------------------------------
# Claim-level summary fields (claim_number, patient_name, policy_number,
# hospital_name, document_count) are DERIVED HERE at read time from the
# claim's documents rather than duplicated/stored inside the claims
# collection. The claims collection itself only ever stores claim-level
# fields (file_no, source_file_url, status, timestamps) - never a copy of
# the OCR payload - so there's exactly one source of truth for OCR data.
# ---------------------------------------------------------------------------
_SUMMARY_FIELD_ALIASES = {
    "claim_number": ["claim_number", "claim_no", "file_number"],
    "patient_name": ["patient_name", "insured_name", "claimant_name", "name"],
    "policy_number": ["policy_number", "policy_no"],
    "hospital_name": ["hospital_name", "hospital"],
}


def _normalize_alias(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


async def _summarize_claim_documents(claim_id: str) -> dict:
    document_count = await documents_collection.count_documents({"claim_id": claim_id})
    summary = {"document_count": document_count}

    remaining = set(_SUMMARY_FIELD_ALIASES.keys())
    if remaining:
        cursor = documents_collection.find(
            {"claim_id": claim_id}, {"all_extracted_entities": 1}
        )
        async for doc in cursor:
            entities = doc.get("all_extracted_entities") or {}
            if not isinstance(entities, dict) or not remaining:
                continue
            normalized_entities = {_normalize_alias(k): v for k, v in entities.items()}
            for field in list(remaining):
                for alias in _SUMMARY_FIELD_ALIASES[field]:
                    value = normalized_entities.get(_normalize_alias(alias))
                    if value not in (None, "", "Not Available"):
                        summary[field] = str(value)
                        remaining.discard(field)
                        break
            if not remaining:
                break

    return summary


async def _assert_claim_exists(claim_id: str):
    claim = await claims_collection.find_one({"_id": to_object_id(claim_id)})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


async def _persist_failed_dispatch_state(
    claim_id: str,
    document_id: str,
    document_type: str,
    error_message: str,
) -> None:
    now = now_utc()
    failure_doc = {
        "claim_id": claim_id,
        "document_id": document_id,
        "document_type": document_type,
        "ocr_status": "failed",
        "status": "failed",
        "raw_ocr_response": {},
        "structured_ocr_data": {},
        "mapped_fields": {},
        "mapping_status": "failed",
        "error_message": error_message,
        "processed_pages": [],
        "pages_processed": [],
        "processed_page_count": 0,
        "total_page_count": 0,
        "global_metadata": {},
        "all_extracted_entities": {},
        "all_extracted_tables": [],
        "warnings": {},
        "created_at": now,
        "updated_at": now,
    }
    result = await documents_collection.update_one(
        {"claim_id": claim_id, "document_type": document_type},
        {"$set": failure_doc},
        upsert=True,
    )
    logger.warning(
        "Persisted failed OCR state for claim=%s document=%s matched=%s modified=%s upserted_id=%s",
        claim_id,
        document_type,
        result.matched_count,
        result.modified_count,
        result.upserted_id,
    )
    claim_result = await claims_collection.update_one(
        {"_id": to_object_id(claim_id)},
        {"$set": {"status": "failed", "updated_at": now, "ocr_error_message": error_message}},
    )
    logger.warning(
        "Marked claim=%s failed after dispatch error matched=%s modified=%s",
        claim_id,
        claim_result.matched_count,
        claim_result.modified_count,
    )


async def _dispatch_ocr_job(
    claim_id: str,
    document_id: str,
    document_type: str,
    file_url: str,
    mime_type: str,
) -> None:
    callback_url = _build_callback_url(claim_id)
    dispatch_url = _build_engine_dispatch_url()
    dispatch_payload = OcrEngineDispatchRequest(
        claim_id=claim_id,
        document_id=document_id,
        document_type=document_type,
        file_url=file_url,
        mime_type=mime_type,
        callback_url=callback_url,
    ).model_dump()

    logger.info(
        "Dispatching OCR job for claim=%s document=%s type=%s engine=%s callback=%s",
        claim_id,
        document_id,
        document_type,
        dispatch_url,
        callback_url,
    )

    try:
        status_code, response_text = await asyncio.to_thread(_post_json, dispatch_url, dispatch_payload)
        if status_code not in {200, 201, 202}:
            raise RuntimeError(f"OCR engine returned HTTP {status_code}: {response_text}")

        claim_result = await claims_collection.update_one(
            {"_id": to_object_id(claim_id)},
            {"$set": {"status": "processing", "updated_at": now_utc()}},
        )
        logger.info(
            "OCR job accepted for claim=%s matched=%s modified=%s response=%s",
            claim_id,
            claim_result.matched_count,
            claim_result.modified_count,
            response_text[:500] if response_text else "",
        )
    except Exception as exc:
        logger.exception("OCR dispatch failed for claim=%s document=%s", claim_id, document_id)
        await _persist_failed_dispatch_state(claim_id, document_id, document_type, str(exc))


async def _create_claim_record(
    payload: ClaimCreateRequest,
    background_tasks: BackgroundTasks,
) -> ClaimResponse:
    now = now_utc()
    claim_doc = {
        "file_no": payload.file_no,
        "source_file_url": payload.source_file_url,
        "source_file_public_id": payload.source_file_public_id,
        "original_filename": payload.original_filename,
        "uploaded_by": payload.uploaded_by,
        "document_type": _normalize_document_type(payload.document_type),
        "mime_type": payload.mime_type,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }
    result = await claims_collection.insert_one(claim_doc)
    claim_doc["_id"] = result.inserted_id
    saved = serialize_doc(claim_doc)

    dispatch_mime_type = _guess_mime_type(saved["source_file_url"], payload.mime_type)
    background_tasks.add_task(
        _dispatch_ocr_job,
        saved["id"],
        saved["id"],
        saved.get("document_type") or DEFAULT_DOCUMENT_TYPE,
        saved["source_file_url"],
        dispatch_mime_type,
    )

    logger.info(
        "Created claim=%s status=uploaded document_type=%s mime_type=%s",
        saved["id"],
        saved.get("document_type") or DEFAULT_DOCUMENT_TYPE,
        dispatch_mime_type,
    )

    return ClaimResponse(
        claim_id=saved["id"],
        file_no=saved.get("file_no"),
        source_file_url=saved["source_file_url"],
        status=saved["status"],
        created_at=saved["created_at"],
        updated_at=saved["updated_at"],
        document_count=0,
    )


@router.post("/upload", response_model=ClaimResponse, status_code=201)
async def upload_and_create_claim(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    file_no: str | None = Form(default=None),
    uploaded_by: str | None = Form(default=None),
    folder: str = Form(default="claims"),
):
    """
    Convenience endpoint: does the Cloudinary upload AND claim creation in
    ONE call, so the frontend doesn't need two separate requests.

    Example (curl):
        curl -X POST http://localhost:8000/claims/upload \
             -F "file=@MEDSAVE.pdf" \
             -F "uploaded_by=reviewer_1"

    Internally this just chains: upload_pdf_to_cloudinary() -> insert claim.
    If you'd rather upload client-side (frontend -> Cloudinary directly),
    use GET /uploads/cloudinary-signature + POST /claims instead - this
    endpoint is purely for convenience when the file passes through your
    backend anyway.
    """
    upload_result = await upload_pdf_to_cloudinary(file, folder=folder)

    payload = ClaimCreateRequest(
        file_no=file_no,
        source_file_url=upload_result["secure_url"],
        source_file_public_id=upload_result["public_id"],
        original_filename=upload_result["original_filename"],
        uploaded_by=uploaded_by,
        document_type=DEFAULT_DOCUMENT_TYPE,
        mime_type=upload_result.get("mime_type"),
    )
    return await _create_claim_record(payload, background_tasks)


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(payload: ClaimCreateRequest, background_tasks: BackgroundTasks):
    """Called right after the frontend uploads the document to Cloudinary."""
    return await _create_claim_record(payload, background_tasks)


@router.get("", response_model=List[ClaimResponse])
async def list_claims(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    skip: int = Query(default=0, ge=0),
):
    query = {}
    if status:
        query["status"] = status

    cursor = (
        claims_collection.find(query)
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        d = serialize_doc(doc)
        summary = await _summarize_claim_documents(d["id"])
        results.append(
            ClaimResponse(
                claim_id=d["id"],
                file_no=d.get("file_no"),
                source_file_url=d["source_file_url"],
                status=d["status"],
                created_at=d["created_at"],
                updated_at=d["updated_at"],
                **summary,
            )
        )
    return results


@router.get("/{claim_id}", response_model=ClaimDetailResponse)
async def get_claim_detail(claim_id: str):
    """This is the main endpoint the FRONTEND calls to render/auto-fill the
    review form. It returns the claim plus every OCR-extracted sub-document
    exactly as the engine produced it (nothing dropped, nothing renamed)."""
    claim = await claims_collection.find_one({"_id": to_object_id(claim_id)})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    docs_cursor = documents_collection.find({"claim_id": claim_id})
    documents_out: List[DocumentOut] = []
    async for doc in docs_cursor:
        documents_out.append(_document_out_from_record(doc))

    claim_s = serialize_doc(claim)
    return ClaimDetailResponse(
        claim_id=claim_s["id"],
        file_no=claim_s.get("file_no"),
        source_file_url=claim_s["source_file_url"],
        status=claim_s["status"],
        document_count=len(documents_out),
        documents=documents_out,
        created_at=claim_s["created_at"],
        updated_at=claim_s["updated_at"],
    )


@router.patch("/{claim_id}/status")
async def update_claim_status(claim_id: str, status: str = Query(...)):
    allowed = {"uploaded", "processing", "completed", "reviewed", "failed"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")

    result = await claims_collection.update_one(
        {"_id": to_object_id(claim_id)},
        {"$set": {"status": status, "updated_at": now_utc()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")

    logger.info(
        "Updated claim=%s status=%s matched=%s modified=%s",
        claim_id,
        status,
        result.matched_count,
        result.modified_count,
    )
    return {"claim_id": claim_id, "status": status}


@router.delete("/{claim_id}", status_code=204)
async def delete_claim(claim_id: str):
    await documents_collection.delete_many({"claim_id": claim_id})
    result = await claims_collection.delete_one({"_id": to_object_id(claim_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")
    return None
