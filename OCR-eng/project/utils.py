import os
import json
import logging
import tiktoken
from datetime import datetime
from . import config                     # Ensure 'configure' matches your exact file name


# Set up clean logging subsystem configuration matching config variables
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding=config.JSON_ENCODING),
        logging.StreamHandler()
    ]
)

encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(encoder.encode(text))

def is_page_blank(text: str) -> bool:
    normalized = text.strip()
    # Check simple character bounds based on config definition
    if len(normalized) < config.MIN_PAGE_CHARACTERS:
        return True
    
    blank_markers = ["page intentionally left blank", "blank page", "no data on this page"]
    return any(marker in normalized.lower() for marker in blank_markers)

def create_blank_page_json(page_num: int) -> dict:
    return {
        "page_number": page_num,
        "document_type_identified": "blank_page",
        "model": config.MODEL_NAME,
        "prompt_version": config.PROMPT_VERSION,
        "processed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "global_metadata": {"patient_name": None, "hospital_name": None, "date": None, "claim_or_policy_number": None},
        "dynamic_entities": {},
        "table_fragment": [],
        "warnings": {"ignored_content": ["empty page signature"], "uncertain_fields": []},
        "usage": {"prompt_tokens": 0, "completion_tokens": 0}
    }

def save_json_atomically(file_path: str, data: dict):
    """Writes to temp directory using config suffixes, then executes atomic swap operations."""
    filename = os.path.basename(file_path)
    temp_filename = filename.replace(config.OUTPUT_EXTENSION, config.TEMP_EXTENSION)
    temp_path = os.path.join(config.TEMP_DIR, temp_filename)
    
    try:
        with open(temp_path, "w", encoding=config.JSON_ENCODING) as f:
            json.dump(
                data, 
                f, 
                indent=config.JSON_INDENT, 
                ensure_ascii=config.ENSURE_ASCII
            )
        # Execute an atomic swap operation
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise IOError(f"Atomic file system swap failure: {e}")
