"""
==========================================================================
Enterprise Medical IDP
Document Merger Configuration
==========================================================================

Purpose
-------
Defines all paths and batching configuration required by the
Document Merger module.

The merger groups OCR pages belonging to the same document type into
fixed-size merged OCR files for downstream LLM JSON extraction.

Example

Hospital Bill
    hospital_bill_001_raw.txt
    hospital_bill_002_raw.txt

Insurance Form
    insurance_form_001_raw.txt
"""

import os


def _parse_optional_page_limit(*env_names: str):
    for env_name in env_names:
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue

        raw_value = raw_value.strip()
        if not raw_value:
            continue

        try:
            parsed = int(raw_value)
        except ValueError:
            continue

        if parsed > 0:
            return parsed

    return None


# ==========================================================================
# BASE OUTPUT
# ==========================================================================

RUN_ID = os.getenv("OCR_CURRENT_RUN_ID") or os.getenv("OCR_RUN_ID")
BASE_OUTPUT = os.getenv("OCR_CURRENT_RESULT_DIR") or os.path.join(
    "RESULT",
    "MEDSAVE"
)
CURRENT_RESULT_DIR = BASE_OUTPUT
MAX_OCR_PAGES = _parse_optional_page_limit("OCR_MAX_PAGES", "MAX_PDF_PAGES")
# NOTE: None means "no cap, process every page" - merger.py already checks
# `is not None` before comparing against it, so leaving MAX_PDF_PAGES blank
# in .env correctly disables the page cap here too.


def configure_runtime_context(result_dir: str | None = None, run_id: str | None = None) -> None:
    """Update merger paths to the active OCR run folder."""
    global BASE_OUTPUT, CURRENT_RESULT_DIR, RUN_ID, OCR_DIR, CLASSIFICATION_DIR, MERGED_OUTPUT_DIR

    if result_dir:
        BASE_OUTPUT = str(result_dir)
        CURRENT_RESULT_DIR = BASE_OUTPUT
    if run_id:
        RUN_ID = run_id

    OCR_DIR = os.path.join(BASE_OUTPUT, "05_ocr")
    CLASSIFICATION_DIR = os.path.join(BASE_OUTPUT, "06_document_classification")
    MERGED_OUTPUT_DIR = os.path.join(BASE_OUTPUT, "08_merged_documents")

# ==========================================================================
# INPUT DIRECTORIES
# ==========================================================================

OCR_DIR = os.path.join(
    BASE_OUTPUT,
    "05_ocr"
)

CLASSIFICATION_DIR = os.path.join(
    BASE_OUTPUT,
    "06_document_classification"
)

# ==========================================================================
# OUTPUT DIRECTORY
# ==========================================================================

MERGED_OUTPUT_DIR = os.path.join(
    BASE_OUTPUT,
    "08_merged_documents"
)

# ==========================================================================
# MERGING CONFIGURATION
# ==========================================================================

# Maximum number of pages per merged OCR file.
#
# Example
#
# insurance_form_001_raw.txt
#     Page 1
#     Page 2
#     ...
#     Page 7
#
# insurance_form_002_raw.txt
#     Page 8
#     Page 9
#
MAX_PAGES_PER_BATCH = 7

# ==========================================================================
# FILE NAMING
# ==========================================================================

OCR_FILE_TEMPLATE = "page_{page}_raw.txt"

CLASSIFICATION_FILE_EXTENSION = ".json"

MERGED_FILE_TEMPLATE = "{document_type}_{batch:03d}_raw.txt"

# ==========================================================================
# ENCODING
# ==========================================================================

ENCODING = "utf-8"

# ==========================================================================
# CREATE OUTPUT DIRECTORY
# ==========================================================================

os.makedirs(
    MERGED_OUTPUT_DIR,
    exist_ok=True
)

# ==========================================================================
# VALIDATION
# ==========================================================================

if not os.path.isdir(OCR_DIR):
    raise FileNotFoundError(
        f"OCR directory not found:\n{OCR_DIR}"
    )

if not os.path.isdir(CLASSIFICATION_DIR):
    raise FileNotFoundError(
        f"Classification directory not found:\n{CLASSIFICATION_DIR}"
    )

# ==========================================================================
# CONFIGURATION SUMMARY
# ==========================================================================

print("=" * 70)
print("Enterprise Medical IDP - Document Merger")
print("=" * 70)
print(f"OCR Folder             : {OCR_DIR}")
print(f"Classification Folder  : {CLASSIFICATION_DIR}")
print(f"Merged Output Folder   : {MERGED_OUTPUT_DIR}")
print(f"Pages Per Batch        : {MAX_PAGES_PER_BATCH}")
print("=" * 70)