# import os
# import gc
# import json
# import time
# import logging
# import re
# import sys
# from datetime import datetime

# import config
# import prompt
# import utils
# import llm_client

# from pathlib import Path

import ast
import gc
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

from . import (
    config,
    llm_client,
    prompt,
    utils,
)
from .llm_client import LLMJsonValidationError

# # def extract_page_number(file_name: str) -> int:
# #     """Extracts the numeric page sequence from filenames like 'page_0.txt' or 'raw_1.txt'."""
# #     numbers = re.findall(r'\d+', file_name)
# #     return int(numbers) if numbers else 0


# # ==========================================================================
# # GET ALL MERGED OCR DOCUMENTS
# # ==========================================================================


def get_merged_documents():
    """Returns every merged OCR document path sequentially."""
    return sorted(Path(config.MERGED_DOCUMENT_DIR).rglob("*_raw.txt"))


_TABLE_KEY_OVERRIDES = {
    "bill_no": "bill_no",
    "sl_no": "sl_no",
    "amount_rs": "amount_rs",
    "exp": "expiry",
    "expiry": "expiry",
}


def _sanitize_json_key(key: str, fallback_index: int | None = None) -> str:
    if key is None:
        return f"column_{fallback_index}" if fallback_index else "column"

    cleaned = str(key).strip().lower()
    if not cleaned:
        return f"column_{fallback_index}" if fallback_index else "column"

    cleaned = cleaned.replace("’", "'")
    cleaned = cleaned.replace('"', "")
    cleaned = cleaned.replace("'", "")
    cleaned = re.sub(r"[\s\./\\[\]\(\)\{\}-]+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_]+", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    cleaned = _TABLE_KEY_OVERRIDES.get(cleaned, cleaned)
    return cleaned or (f"column_{fallback_index}" if fallback_index else "column")


def _repair_malformed_json_keys(raw_text: str) -> str:
    # Examples that must remain unchanged:
    # "admin_time": "10:39:00 AM"
    # "policy_from": "01/12/2024"
    # Malformed key that should be repaired:
    # "Bill No.': "Hospital main Bill" -> "bill_no": "Hospital main Bill"
    def _replace(match: re.Match) -> str:
        prefix = match.group(1)
        repaired_key = _sanitize_json_key(match.group(2))
        return f'{prefix}"{repaired_key}":'

    return re.sub(
        r'([{\[,]\s*)"([^"\\r\\n]+?)\s*(?:[\'’])?\s*:',
        _replace,
        raw_text,
    )


def _repair_json_text(raw_text: str) -> str:
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    cleaned = cleaned.replace("\\'", "'")
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    repaired = _repair_malformed_json_keys(cleaned)
    if repaired != cleaned:
        logging.warning("Repaired malformed JSON keys before parsing.")
        cleaned = repaired
    return cleaned.strip()


def _parse_llm_payload(raw_text: str):
    cleaned = _repair_json_text(raw_text)
    candidates = [cleaned]

    if "{" in cleaned and "}" in cleaned:
        candidates.append(cleaned[cleaned.find("{") : cleaned.rfind("}") + 1])

    last_error = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            last_error = exc

        pythonish = re.sub(r"\bnull\b", "None", candidate, flags=re.IGNORECASE)
        pythonish = re.sub(r"\btrue\b", "True", pythonish, flags=re.IGNORECASE)
        pythonish = re.sub(r"\bfalse\b", "False", pythonish, flags=re.IGNORECASE)

        try:
            parsed = ast.literal_eval(pythonish)
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            last_error = exc

    raise ValueError(f"Unable to parse LLM JSON payload: {last_error}")


def _sanitize_table_payload(payload: dict) -> dict:
    tables = payload.get("all_extracted_tables")
    if not isinstance(tables, list):
        return payload

    sanitized_tables = []
    for table in tables:
        if not isinstance(table, dict):
            sanitized_tables.append(table)
            continue

        sanitized_table = dict(table)
        headers = sanitized_table.get("headers")
        if isinstance(headers, list):
            sanitized_table["headers"] = [
                _sanitize_json_key(header, index + 1)
                for index, header in enumerate(headers)
            ]

        rows = sanitized_table.get("rows")
        if isinstance(rows, list):
            sanitized_rows = []
            for row in rows:
                if isinstance(row, dict):
                    sanitized_row = {}
                    for index, (key, value) in enumerate(row.items(), start=1):
                        sanitized_key = _sanitize_json_key(key, index)
                        candidate_key = sanitized_key
                        suffix = 2
                        while candidate_key in sanitized_row:
                            candidate_key = f"{sanitized_key}_{suffix}"
                            suffix += 1
                        sanitized_row[candidate_key] = value
                    sanitized_rows.append(sanitized_row)
                else:
                    sanitized_rows.append(row)
            sanitized_table["rows"] = sanitized_rows

        sanitized_tables.append(sanitized_table)

    payload["all_extracted_tables"] = sanitized_tables
    return payload


def _call_llm_and_get_json(system_prompt: str, user_prompt: str, output_name: str):
    """Calls Groq and returns (raw_json_string, usage_dict).

    Groq's strict JSON mode sometimes REJECTS the model's own malformed
    output outright (json_validate_failed) rather than returning it as a
    normal completion - previously that meant the entire document's
    extraction was thrown away and replaced with an empty partial payload,
    even when the rejected text was a small, fixable issue (e.g. the
    'Bill No.': -> unterminated-key pattern _repair_malformed_json_keys
    already knows how to fix).

    Recovery order:
      1. Try the call normally.
      2. If Groq rejects the JSON, run the raw rejected text through our
         existing local repair pipeline (_parse_llm_payload) - no extra API
         call needed.
      3. If local repair still can't produce a dict, retry the API call
         ONCE more (LLM sampling is non-deterministic, so a second attempt
         often just produces valid JSON on its own).
      4. Only after that do we give up and let the caller fall back to an
         empty partial payload.
    """
    try:
        api_response = llm_client.call_groq_with_resilience(system_prompt, user_prompt)
        return api_response.choices[0].message.content, {
            "prompt_tokens": api_response.usage.prompt_tokens,
            "completion_tokens": api_response.usage.completion_tokens,
        }
    except LLMJsonValidationError as json_fault:
        if json_fault.failed_generation:
            try:
                _parse_llm_payload(json_fault.failed_generation)
                logging.info(
                    "🔧 Recovered %s from Groq's rejected JSON via local repair (no extra API call).",
                    output_name,
                )
                return json_fault.failed_generation, {"prompt_tokens": None, "completion_tokens": None}
            except Exception:
                logging.warning(
                    "Local repair of %s's rejected JSON failed too - retrying the API call once.",
                    output_name,
                )

        # Local repair didn't work (or there was no failed_generation text
        # to repair) - one bounded retry before giving up to the caller.
        api_response = llm_client.call_groq_with_resilience(system_prompt, user_prompt)
        return api_response.choices[0].message.content, {
            "prompt_tokens": api_response.usage.prompt_tokens,
            "completion_tokens": api_response.usage.completion_tokens,
        }


def _build_partial_payload(
    document_type: str, pages_processed: list[int], error_message: str
) -> dict:
    """document_type must be the CLASSIFIED type (e.g. 'insurance_form'),
    not the output filename stem (e.g. 'insurance_form_001') - the stem
    includes the per-claim sequence suffix and was previously being stored
    here by mistake, corrupting document_type for every failed extraction
    (backend/frontend grouping and labels then showed 'Insurance Form 001'
    instead of 'Insurance Form')."""
    return {
        "document_type": document_type,
        "pages_processed": pages_processed,
        "global_metadata": {},
        "all_extracted_entities": {},
        "all_extracted_tables": [],
        "llm_json_errors": [error_message],
        "warnings": {
            "ignored_handwritten_content": [],
            "unmapped_ambiguous_text_regions": [],
            "errors": [error_message],
        },
        "errors": [error_message],
    }


def get_user_routing_choice() -> bool:
    """Displays an interactive menu inside the terminal window to route processing behavior."""
    print("\n" + "=" * 50)
    print("  Enterprise Pipeline Processing Mode Selection")
    print("=" * 50)
    print(" [1] CONTINUE   - Skip existing JSON files, pick up where it stopped.")
    print(" [2] RE-EXTRACT - Wipe old data and process everything from Page 1.")
    print("=" * 50)
    
    while True:
        choice = input("Please enter your choice option (1 or 2): ").strip()
        if choice == "1":
            print("\n>>> Selected Selection: CONTINUE (Idempotency mode enabled)\n")
            return False  
        elif choice == "2":
            confirm = input("Are you absolutely sure you want to overwrite previous runs? (y/n): ").strip().lower()
            if confirm == "y":
                print("\n>>> Selected Selection: RE-EXTRACT (Overwriting old files)\n")
                return True  
            else:
                print("\nOperation cancelled. Please select option again.")
        else:
            print("Invalid input. Please enter exactly 1 or 2.")

def run_extraction_pipeline(force_reprocess_active: bool = None):
    """
    Core IDP processing module designed to be executed directly 
    or called programmatically by a master coordinator script.
    """
    # If not passed programmatically by main.py, trigger terminal fallback menu
    if force_reprocess_active is None:
        force_reprocess_active = get_user_routing_choice()

    logging.info("======= Commencing Production Medical IDP Pipeline =======")
    
    if not os.path.exists(config.MERGED_DOCUMENT_DIR):
        logging.error(f"Merged OCR Directory not found at: {config.MERGED_DOCUMENT_DIR}")
        return

    raw_files = get_merged_documents()
    total_files = len(raw_files)
    
    logging.info(f"Identified {total_files} text files ready for parsing processing.")

    for idx, file_name in enumerate(raw_files):
        output_name = file_name.stem.replace("_raw", "")
        final_output_path = os.path.join(config.PARSED_DIR, output_name + config.OUTPUT_EXTENSION)
        input_txt_path = str(file_name)
        
        # 2. Dynamic Routing Logic Selection Checks
        if os.path.exists(final_output_path):
            if not force_reprocess_active:
                logging.info(f"[{idx+1}/{total_files}] Page {output_name} already processed. Skipping.")
                continue
            else:
                logging.info(f"[{idx+1}/{total_files}] Force re-parsing Page {output_name} (Overwriting old run)...")
        else:
            logging.info(f"[{idx+1}/{total_files}] Processing {file_name.name}")
        
        # 3. Read Content asset strings
        with open(input_txt_path, "r", encoding=config.JSON_ENCODING) as f:
            raw_text = f.read()
            
        # 4. Empty Page Protection Check
        if utils.is_page_blank(raw_text):
            logging.info(f"Page {output_name} validation confirmed blank conditions. Writing placeholder.")
            blank_json = {
                "document_name": output_name,
                "status": "blank_document"
            }
            utils.save_json_atomically(final_output_path, blank_json)
            continue
            
        # 5. Token Bounds Truncation Protection
        if len(raw_text) > config.MAX_CHARS:
            logging.warning(f"Page {output_name} data ceiling exceeded. Applying safe truncation updates.")
            raw_text = raw_text[:config.MAX_CHARS] + "\n[DATA CEILING TRUNCATION APPLIED]"
            
        # 6. Prompt Injection setup
        document_type = file_name.parent.name

        # Regular Expression to dynamically capture array elements
        pages_match = re.search(r"PAGES INCLUDED\s*:\s*\[(.*?)\]", raw_text)
        if pages_match:
            # Split items by comma, remove whitespace and quotes to build a clean numeric array
            pages_processed = [int(p.strip()) for p in pages_match.group(1).split(",") if p.strip().isdigit()]
        else:
            pages_processed = []

        user_prompt = prompt.get_user_prompt(
            document_type=document_type,
            pages_processed=pages_processed,
            merged_text=raw_text
        )
        
        # 7. Execute resilient call loops
        try:
            api_start = time.time()
            raw_json_string, usage = _call_llm_and_get_json(prompt.SYSTEM_PROMPT, user_prompt, output_name)

            try:
                parsed_payload = _parse_llm_payload(raw_json_string)
            except Exception as parse_error:
                logging.error(
                    "❌ JSON parse failed for %s; writing partial payload instead: %s",
                    output_name,
                    parse_error,
                )
                partial_payload = _build_partial_payload(document_type, pages_processed, str(parse_error))
                partial_payload["page_number"] = int(output_name) if output_name.isdigit() else output_name
                partial_payload["document_type_classified"] = document_type
                partial_payload["processed_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                utils.save_json_atomically(final_output_path, partial_payload)
                continue

            parsed_payload["model"] = config.MODEL_NAME
            parsed_payload["prompt_version"] = config.PROMPT_VERSION
            parsed_payload["processed_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            parsed_payload["usage"] = usage
            parsed_payload = _sanitize_table_payload(parsed_payload)

            # 8. Commit data atomically
            utils.save_json_atomically(final_output_path, parsed_payload)
            logging.info(f"Successfully extracted JSON for {output_name} in {round(time.time() - api_start, 2)} seconds.")

        except Exception as loop_fault:
            logging.error(f"❌ System Exception fault detected on Document {output_name}: {loop_fault}")
            partial_payload = _build_partial_payload(document_type, pages_processed, str(loop_fault))
            partial_payload["page_number"] = int(output_name) if output_name.isdigit() else output_name
            partial_payload["document_type_classified"] = document_type
            partial_payload["processed_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            utils.save_json_atomically(final_output_path, partial_payload)
            
    logging.info("======= Enterprise Medical IDP Pipeline Complete =======")

# Retain ability to run independently by hitting this execution entrypoint block directly
if __name__ == "__main__":
    run_extraction_pipeline()