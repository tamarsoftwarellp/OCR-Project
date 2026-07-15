"""
Pydantic models.

IMPORTANT: `all_extracted_entities` and `all_extracted_tables` are intentionally
typed as Dict[str, Any] / List[Any] because the OCR engine emits DYNAMIC
snake_case keys that differ per document. We do NOT want a rigid schema here
- we save whatever the OCR engine gives us, exactly as-is.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Claim creation (called by frontend right after Cloudinary upload)
# ---------------------------------------------------------------------------
class ClaimCreateRequest(BaseModel):
    file_no: Optional[str] = None
    source_file_url: str
    source_file_public_id: Optional[str] = None
    original_filename: Optional[str] = None
    uploaded_by: Optional[str] = None
    document_type: Optional[str] = "claim_pdf"
    mime_type: Optional[str] = None


class ClaimResponse(BaseModel):
    claim_id: str
    file_no: Optional[str] = None
    source_file_url: str
    status: str
    created_at: datetime
    updated_at: datetime

    # Derived at read time from the claim's documents (never stored as a
    # copy of the OCR payload inside the claims collection itself - see
    # notes in routers/claims.py::_summarize_claim_documents).
    document_count: int = 0
    claim_number: Optional[str] = None
    patient_name: Optional[str] = None
    policy_number: Optional[str] = None
    hospital_name: Optional[str] = None


# ---------------------------------------------------------------------------
# 2. OCR result ingestion (called by the OCR engine / worker once processing
#    of ONE document_type is complete, e.g. "insurance_form", "invoice", etc.)
#    This mirrors the exact JSON shape produced by project/final_json_creation.py
# ---------------------------------------------------------------------------
class Warnings(BaseModel):
    ignored_handwritten_content: List[str] = Field(default_factory=list)
    unmapped_ambiguous_text_regions: List[str] = Field(default_factory=list)


class OcrDocumentIngestRequest(BaseModel):
    document_type: str
    pages_processed: List[int] = Field(default_factory=list)
    global_metadata: Dict[str, Any] = Field(default_factory=dict)
    all_extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    all_extracted_tables: List[Any] = Field(default_factory=list)
    warnings: Warnings = Field(default_factory=Warnings)

    # identity - lets a claim hold MULTIPLE documents of the same
    # document_type (invoice #1, invoice #2, ...) without overwriting.
    source_file_name: Optional[str] = None
    sequence: Optional[int] = None

    # optional trace metadata the engine already emits
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    processed_at: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class OcrDocumentBulkIngestRequest(BaseModel):
    """Used when the engine finishes an entire claim and wants to push
    every classified sub-document (insurance_form, invoice, discharge_summary...)
    in one call."""

    documents: List[OcrDocumentIngestRequest]


class OcrEngineDispatchRequest(BaseModel):
    claim_id: str
    document_id: str
    document_type: str
    file_url: str
    mime_type: str
    callback_url: str


class OcrEngineCallbackRequest(BaseModel):
    claim_id: str
    document_id: str
    document_type: str = "claim_pdf"
    ocr_status: str
    status: Optional[str] = None
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    pdf_name: Optional[str] = None
    raw_ocr_response: Any = Field(default_factory=dict)
    structured_ocr_data: Any = Field(default_factory=dict)
    mapped_fields: Any = Field(default_factory=dict)
    mapping_status: Optional[str] = None
    error_message: Optional[str] = None
    processed_pages: List[int] = Field(default_factory=list)
    processed_page_count: Optional[int] = None
    total_page_count: Optional[int] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# 3. What the frontend receives to render/auto-fill the review form
# ---------------------------------------------------------------------------
class DocumentOut(BaseModel):
    id: str
    document_id: Optional[str] = None
    document_type: str
    source_file_name: Optional[str] = None
    sequence: Optional[int] = None
    pages_processed: List[int]
    global_metadata: Dict[str, Any]
    all_extracted_entities: Dict[str, Any]
    all_extracted_tables: List[Any]
    warnings: Warnings
    ocr_status: Optional[str] = None
    raw_ocr_response: Any = Field(default_factory=dict)
    structured_ocr_data: Any = Field(default_factory=dict)
    mapped_fields: Any = Field(default_factory=dict)
    mapping_status: Optional[str] = None
    error_message: Optional[str] = None
    processed_page_count: Optional[int] = None
    total_page_count: Optional[int] = None
    # Reviewer-entered data, kept strictly separate from the OCR output above -
    # updating these NEVER touches all_extracted_entities/all_extracted_tables.
    review_status: str = "pending"
    entity_verification: Dict[str, bool] = Field(default_factory=dict)
    entity_remarks: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentSummary(BaseModel):
    """Lightweight shape for GET /claims/{claim_id}/documents - just enough
    for the frontend to render dynamic tabs/cards WITHOUT ever hardcoding
    document types and without pulling the full OCR payload per document."""

    id: str
    document_type: str
    source_file_name: Optional[str] = None
    sequence: Optional[int] = None
    pages_processed: List[int]
    ocr_status: Optional[str] = None
    review_status: str = "pending"
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClaimDetailResponse(BaseModel):
    claim_id: str
    file_no: Optional[str] = None
    source_file_url: str
    status: str
    document_count: int = 0
    documents: List[DocumentOut]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# 4. Reviewer correction (PATCH one field inside one document's entities)
# ---------------------------------------------------------------------------
class EntityUpdateRequest(BaseModel):
    key: str
    value: Any
    verified: Optional[bool] = None
    remarks: Optional[str] = None


# ---------------------------------------------------------------------------
# 4b. Reviewer correction for tables (replace the WHOLE all_extracted_tables
#     array in one shot). Tables are dynamic (headers differ per document),
#     so instead of patching individual cells server-side, the frontend
#     sends the full edited array it already has in memory and we persist it
#     as-is - same "trust the caller's shape" approach as OCR ingestion.
# ---------------------------------------------------------------------------
class TablesUpdateRequest(BaseModel):
    tables: List[Any]


# ---------------------------------------------------------------------------
# 5. Auth (signup / login / refresh) - single admin/reviewer role, no
#    role field. Password hash is NEVER returned to the client.
# ---------------------------------------------------------------------------
class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    created_at: datetime