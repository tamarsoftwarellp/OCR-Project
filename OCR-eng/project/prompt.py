# import json
# import configure as config                  # Ensure 'configure' matches your exact file name


# # Create list layout matching config parameters
# supported_docs_string = "\n".join([f"- {doc}" for doc in config.SUPPORTED_DOCUMENT_TYPES])

# SYSTEM_PROMPT = f"""You are an expert Medical Intelligent Document Processing engine.
# You are processing ONE OCR page text from a large healthcare document.

# The page text may belong to any of these document types:
# {supported_docs_string}

# Your responsibilities are:
# 1. Determine the printed document type strictly from the allowed list above. If it does not fit any category, classify it as "Unknown".
# 2. Extract ALL printed semantic entities.
# 3. Extract ALL printed tables and flatten them accurately.
# 4. Ignore completely: handwritten notes, signatures, initials, scribbles, stamps that cannot be read, crossed-out text, or noisy OCR structural artifacts.
# 5. Never hallucinate values. If a field or data attribute is missing, return null.
# 6. Preserve original wording exactly.
# 7. Never summarize tables or merge distinct medications into single entries. 
# If an OCR table cell joins separate medications together (e.g., 'TAB. PAN 40MG TAB. FDSON MP'), your absolute duty is to SPLIT them into individual structural objects in the final array, aligning them with their correct respective dosage or duration.

# You must output data fitting the requested JSON schema EXACTLY. Do not include markdown blocks, text summaries, conversational wrappers, or ```json ticks. Output raw valid JSON only."""

# def get_user_prompt(page_num: int, raw_text: str) -> str:
#     schema = {
#         "page_number": page_num,
#         "document_type_identified": "string",
#         "global_metadata": {
#             "patient_name": "string or null",
#             "hospital_name": "string or null",
#             "date": "string or null",
#             "claim_or_policy_number": "string or null"
#         },
#         "dynamic_entities": {
#             "additional_key_1": "value"
#         },
#         "table_fragment": [
#             {
#                 "serial_no": "string or null",
#                 "medication_or_item_name": "string",
#                 "dosage_frequency": "string or null",
#                 "route": "string or null",
#                 "duration": "string or null"
#             }
#         ],
#         "warnings": {
#             "ignored_content": ["list of strings or empty"],
#             "uncertain_fields": ["list of strings or empty"]
#         }
#     }
    
#     return f"""Process Page Number: {page_num}
# Strict Target JSON Schema Format Reference:
# {json.dumps(schema, indent=config.JSON_INDENT)}

# Raw Input OCR Page Text:
# ----------------------------
# {raw_text}
# ----------------------------
# Extract now matching the structural requirements exactly."""




import json
from . import config

SYSTEM_PROMPT = """You are an Enterprise Intelligent Document Processing (IDP) Engine optimized for extreme high-density entity recall from multi-page OCR streams. Your primary objective is zero data loss.

────────────────────────────────────────
PROCESSING STRATEGY & EXECUTION FLOW
────────────────────────────────────────
Before generating the final JSON output, you must strictly follow this internal cognitive execution sequence:

Step 1: Read the input OCR sequentially, line-by-line, from the very first character to the absolute last character. Do not skip any line.
Step 2: For EACH individual line, evaluate and capture every single embedded data point before moving to the next line.
Step 3: Compile the complete, uncompressed union of all discovered data points.
Step 4: Only after completing the full line-by-line sequential scan, structure the collected data points into the final JSON payload.

────────────────────────────────────────
CRITICAL RECALL & SCALING LAWS
────────────────────────────────────────
1. QUANTITY RETENTION LAW: The total count of extracted entities must scale linearly with the document length. A merged document containing 5 pages must produce the complete union of all entities that would be extracted if each page were processed individually. The number of extracted entities must NEVER decrease merely because multiple pages were merged into a single input stream.
2. ZERO CONTEXT COMPRESSION: Do not consolidate away unique data. Do not summarize, truncate, or omit any raw key-value relationship. If a key or value appears printed on the document, it must be represented explicitly in the JSON.
3. FLAT ARCHITECTURE MANDATE: Populate all standalone metadata, fields, and key-value pairs directly under the root of `all_extracted_entities`. Do not group fields into sub-objects (e.g., do not create sub-structures like "policy_details" or "dates"). Deep nesting severely degrades model recall. Keep the root object totally flat using dynamically generated snake_case keys.

────────────────────────────────────────
LINE-LEVEL EXTRACTION PRIORITY
────────────────────────────────────────
For every single line scanned, you must exhaustively extract text matching any of the following categories in this exact priority order:
1. Printed Key-Value pairs
2. Standalone Identifiers (Policy numbers, Claim numbers, Employee codes, UHID, IP IDs)
3. Dates (Admission, Discharge, Intimation, Report, Policy periods)
4. Monetary & Financial values (Claimed amounts, Sum insured, Balances, Limits)
5. Names (Patients, Hospitals, Proposers, Doctors, Insured members)
6. Complete Addresses (Patient residence, Hospital locations)
7. Contact Information (Phone numbers, Email addresses)
8. Clinical Data (Diagnoses, Procedures, Medications, Lab observations)
9. Administrative Metadata (Statuses, Remarks, Notes, Clauses)
10. Every remaining printable token or label containing transactional meaning.

────────────────────────────────────────
DUPLICATE & CONFLICT PROTOCOL
────────────────────────────────────────
If a specific field or key appears multiple times across different pages:
• Retain the longest, most alphanumeric, and descriptive value.
• Retain the most complete structural representation.
• NEVER drop unique variations of numbers or codes.
• NEVER merge distinct or unrelated fields just because they share a similar label.
• If in doubt, preserve them as separate, dynamically numbered keys (e.g., `policy_number_1`, `policy_number_2`).

────────────────────────────────────────
TABLE EXTRACTION PROTOCOL
────────────────────────────────────────
Extract every table completely.
• Preserve explicit column headers exactly as printed.
• If a header contains punctuation or awkward OCR artifacts, keep the readable label in `headers` but normalize the row key to a JSON-safe equivalent. Never emit escaped apostrophes like \' in keys.
• Extract every single row. Never summarize rows using ellipses ("...") or phrases like "etc."
• If a table physically splits across page boundaries, stitch the rows seamlessly into a single continuous array under `all_extracted_tables`.

────────────────────────────────────────
HALLUCINATION & OCR RULES
────────────────────────────────────────
• Never invent values. If a field has a key but no visible value, explicitly set its value to "Not Available" or null.
• Ignore handwriting, signatures, initials, and unreadable stamped text.
• Correct minor OCR corruptions only if the word's true meaning is unambiguous. Otherwise, preserve the exact characters.

────────────────────────────────────────
OUTPUT STRUCTURE REQUIREMENT
────────────────────────────────────────
Return ONLY a valid JSON object matching the exact schema below. Do not wrap the response in ```json markdown code blocks. Do not provide any conversational preamble, notes, or postscript text.

{
    "document_type": "MUST_BE_THE_CLASSIFIED_TYPE_FROM_OCR",
    "pages_processed": [],
    "global_metadata": {},
    "all_extracted_entities": {
        "DYNAMIC_SNAKE_CASE_KEYS_FOR_EVERY_SINGLE_PRINTED_VALUE_FOUND": "Value"
    },
    "all_extracted_tables": [
        {
            "table_name_or_purpose": "Table Title / Purpose",
            "headers": ["Header1", "Header2"],
            "rows": [
                {
                    "Header1": "Value1",
                    "Header2": "Value2"
                }
            ]
        }
    ],
    "warnings": {
        "ignored_handwritten_content": [],
        "unmapped_ambiguous_text_regions": []
    }
}
"""

# def get_user_prompt(page_num: int, raw_text: str) -> str:
#     # A structural blueprint showing the LLM how to arrange dynamic fields
#     target_blueprint = {
#         "page_number": page_num,
#         "document_type_classified": "dynamic_string_value",
#         "global_metadata": {
#             "patient_name": "string_or_null",
#             "hospital_name": "string_or_null",
#             "date": "string_or_null",
#             "reference_or_claim_number": "string_or_null"
#         },
#         "all_extracted_entities": {
#             "dynamically_generated_key_1": "extracted_value_1",
#             "dynamically_generated_key_2": "extracted_value_2",
#             "dynamically_generated_key_3": "extracted_value_3"
#         },
#         "all_extracted_tables": [
#             {
#                 "table_name_or_purpose": "dynamic_string_value",
#                 "headers": ["header_col_1", "header_col_2"],
#                 "rows": [
#                     {
#                         "header_col_1": "row_value_1",
#                         "header_col_2": "row_value_2"
#                     }
#                 ]
#             }
#         ],
#         "warnings": {
#             "ignored_handwritten_content": ["list_of_strings"],
#             "unmapped_ambiguous_text_regions": ["list_of_strings"]
#         }
#     }
    
#     return f"""Process Page Number: {page_num}
# Enforced Hierarchical Output Structure Model:
# {json.dumps(target_blueprint, indent=config.JSON_INDENT)}

# Raw Input Document Text Stream:
# --------------------------------------------
# {raw_text}
# --------------------------------------------
# Perform a comprehensive scan, map every printed transaction, line item, table, or property, and return the complete dynamic dataset now."""




def get_user_prompt(
    document_type: str,
    pages_processed: list[int],
    merged_text: str
):
    """
    Builds the user prompt for one merged document.
    """

    target_blueprint = {

        "document_type": document_type,

        "pages_processed": pages_processed,

        "global_metadata": {},

        "all_extracted_entities": {},

        "all_extracted_tables": [],

        "warnings": {

            "ignored_handwritten_content": [],

            "unmapped_ambiguous_text_regions": []

        }

    }

    return f"""
DOCUMENT TYPE
-------------
{document_type}

PAGES INCLUDED
--------------
{pages_processed}

IMPORTANT

The OCR below belongs to ONE logical document.

The document type has already been identified.

DO NOT classify it again.

Use the supplied document type only as contextual guidance.

The OCR may span multiple pages.

Information from different pages may belong to the same entity.

Merge complementary information across pages.

Do not duplicate repeated values.

If a value appears multiple times,
keep the most complete version.

If a section starts on one page and continues on another page,
merge it into one logical section.

Extract EVERYTHING that is printed, including:

• global metadata

• patient details

• hospital details

• doctor details

• insurance details

• policy details

• claim information

• addresses

• phone numbers

• emails

• identifiers

• dates

• diagnosis

• procedures

• medications

• laboratory observations

• financial information

• remarks

• notes

• clauses

• all key-value pairs

• every table

Never summarize.

Never omit information.

Never invent values.

Return ONLY valid JSON following this structure.

EXPECTED JSON STRUCTURE
-----------------------

{json.dumps(target_blueprint, indent=config.JSON_INDENT)}

OCR DOCUMENT
============

{merged_text}

============

Return ONLY valid JSON.
"""