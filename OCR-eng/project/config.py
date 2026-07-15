"""
==========================================================================
Enterprise Medical IDP Configuration
==========================================================================
"""

import os
import re
from datetime import datetime, timezone

# ==========================================================================
# PROJECT ROOT (Resolves paths relative to 'New folder2')
# ==========================================================================

# Base directory of this configure.py file (C:\...\New folder2\project)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up exactly one level to step out of 'project/' and hit 'New folder2/' base root
BASE_DIR = os.path.dirname(PROJECT_DIR)

# Points to C:\...\New folder2\result
def _safe_path_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned or fallback


RESULT_ROOT = os.getenv("OCR_RESULT_ROOT", os.path.join(BASE_DIR, "RESULT"))
RUN_ID = os.getenv("OCR_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
JOB_SCOPE = _safe_path_segment(
    os.getenv("OCR_CLAIM_ID")
    or os.getenv("CLAIM_ID")
    or os.getenv("OCR_DOCUMENT_ID")
    or os.getenv("DOCUMENT_ID"),
    "job",
)

RESULT_DIR = os.path.join(RESULT_ROOT, JOB_SCOPE, RUN_ID)
CURRENT_RESULT_DIR = RESULT_DIR

# ==========================================================================
# API
# ==========================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY environment variable not found."
    )

MODEL_NAME = "llama-3.3-70b-versatile"

PROMPT_VERSION = "v1.2.0"

# ==========================================================================
# REQUESTS
# ==========================================================================

MAX_RETRIES = 5

INITIAL_BACKOFF = 2

REQUEST_TIMEOUT = 120


# ==========================================================
# LLM OUTPUT
# ==========================================================

MAX_OUTPUT_TOKENS = 4000


# ==========================================================================
# RATE LIMIT
# ==========================================================================

MAX_REQUESTS_PER_MINUTE = 30

API_PACING_DELAY = 60 / MAX_REQUESTS_PER_MINUTE

# ==========================================================================
# OCR
# ==========================================================================

MAX_CHARS = 25000

MIN_PAGE_CHARACTERS = 15


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


MAX_OCR_PAGES = _parse_optional_page_limit("OCR_MAX_PAGES", "MAX_PDF_PAGES")
# NOTE: leave this as None when unset/empty - it means "no cap, process every
# page". main.py already handles None correctly (page_limit_setting shows
# "ALL", and convert_pdf_to_images(max_pages=None) converts the whole PDF).
# A previous `or 10` here silently forced every run to a 10-page cap even
# when MAX_PDF_PAGES was deliberately left blank in .env to mean "no limit".

# ==========================================================================
# INPUT (Points directly to C:\...\New folder2\result\05_ocr)
# ==========================================================================

IMAGE_DIR = os.path.join(CURRENT_RESULT_DIR, "01_images")
ENHANCED_DIR = os.path.join(CURRENT_RESULT_DIR, "02_enhanced")
LAYOUT_DIR = os.path.join(CURRENT_RESULT_DIR, "03_layout")
REGIONS_DIR = os.path.join(CURRENT_RESULT_DIR, "04_regions")
OCR_DIR = os.path.join(CURRENT_RESULT_DIR, "05_ocr")
CLASSIFICATION_DIR = os.path.join(CURRENT_RESULT_DIR, "06_document_classification")
MERGED_OUTPUT_DIR = os.path.join(CURRENT_RESULT_DIR, "08_merged_documents")
MERGED_DOCUMENT_DIR = MERGED_OUTPUT_DIR

# ==========================================================================
# OUTPUT (Points directly to C:\...\New folder2\result\06_llm_json)
# ==========================================================================

PARSED_DIR = os.path.join(CURRENT_RESULT_DIR, "09_llm_json")

FINAL_OUTPUT_PATH = os.path.join(CURRENT_RESULT_DIR, "final_output.json")
FINAL_PAYLOAD_PATH = os.path.join(CURRENT_RESULT_DIR, "final_payload.json")

# ==========================================================================
# LOGGING
# ==========================================================================

LOG_DIR = os.path.join(BASE_DIR, "logs")

LOG_FILE = os.path.join(LOG_DIR, "llm_parser.log")

# ==========================================================================
# TEMP FILES
# ==========================================================================

TEMP_DIR = os.path.join(BASE_DIR, "temp")

# ==========================================================================
# JSON
# ==========================================================================

JSON_INDENT = 4

JSON_ENCODING = "utf-8"

ENSURE_ASCII = False

# ==========================================================================
# FILE NAMING
# ==========================================================================

INPUT_EXTENSION = "_raw.txt"

OUTPUT_EXTENSION = ".json"

TEMP_EXTENSION = ".tmp"

RAW_SUFFIX = "_raw"

# ==========================================================================
# EXTRACTION
# ==========================================================================

STRICT_JSON_MODE = True

IGNORE_HANDWRITTEN = True

ALLOW_NULL_FIELDS = True

PRESERVE_TABLE_LAYOUT = True

# ==========================================================================
# MEMORY
# ==========================================================================

ENABLE_GARBAGE_COLLECTION = True

DELETE_INTERMEDIATE_OBJECTS = True

# ==========================================================================
# DOCUMENT TYPES
# ==========================================================================

SUPPORTED_DOCUMENT_TYPES = [
    "Hospital Bill",
    "Itemized Invoice",
    "Insurance Claim Form",
    "Cashless Authorization",
    "Discharge Summary",
    "Laboratory Report",
    "Radiology Report",
    "Pharmacy Receipt",
    "Prescription",
    "Medical Certificate",
    "Patient Registration Form",
    "Consent Form",
    "Unknown"
]

# ==========================================================================
# CREATE DIRECTORIES
# ==========================================================================

for path in [
    RESULT_ROOT,
    CURRENT_RESULT_DIR,
    IMAGE_DIR,
    ENHANCED_DIR,
    LAYOUT_DIR,
    REGIONS_DIR,
    OCR_DIR,
    CLASSIFICATION_DIR,
    MERGED_OUTPUT_DIR,
    PARSED_DIR,
    LOG_DIR,
    TEMP_DIR,
]:
    os.makedirs(path, exist_ok=True)

# ==========================================================================
# VALIDATION
# ==========================================================================

# ==========================================================================
# CONFIGURATION SUMMARY
# ==========================================================================

print("=" * 70)
print("Enterprise Medical IDP Configuration (Updated File Architecture)")
print("=" * 70)
print(f"Model              : {MODEL_NAME}")
print(f"Prompt Version     : {PROMPT_VERSION}")
print(f"Run ID             : {RUN_ID}")
print(f"Result Directory   : {CURRENT_RESULT_DIR}")
print(f"OCR Input Folder   : {MERGED_DOCUMENT_DIR}")
print(f"JSON Output Folder : {PARSED_DIR}")
print(f"Logs               : {LOG_FILE}")
print(f"API Delay          : {API_PACING_DELAY:.2f} sec")
print("=" * 70)