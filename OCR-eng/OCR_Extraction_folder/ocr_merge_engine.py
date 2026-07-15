import os
import json
import numpy as np

from OCR_Extraction_folder.table_grid_detector import (

    detect_table_cells,
    assign_ocr_to_cells

)

from External.extraction.spatial_utils import group_tokens_into_rows

from External.extraction.kv_mapper import map_key_values

from External.core.semantic_normalizer import normalize_kv_pairs


# =========================================================
# SORT OCR TOKENS
# =========================================================

def sort_global_ocr(ocr_results):

    return sorted(

        ocr_results,

        key=lambda x: (

            x.get("y", 0),
            x.get("x", 0)

        )

    )


# =========================================================
# REMOVE DUPLICATE OCR TOKENS
# =========================================================

def remove_duplicate_tokens(ocr_results):

    unique = []

    seen = set()

    for item in ocr_results:

        text = item.get("text", "").strip()

        x = item.get("x", 0)
        y = item.get("y", 0)

        key = (

            text.lower(),
            round(x / 5),
            round(y / 5)

        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(item)

    return unique


# =========================================================
# GROUP OCR INTO LINES
# =========================================================

def group_ocr_lines(

    ocr_results,

    y_threshold=25

):

    if len(ocr_results) == 0:

        return []

    sorted_results = sort_global_ocr(

        ocr_results

    )

    grouped_lines = []

    current_line = [

        sorted_results[0]

    ]

    previous_y = sorted_results[0]["y"]

    for item in sorted_results[1:]:

        current_y = item["y"]

        if abs(current_y - previous_y) <= y_threshold:

            current_line.append(item)

        else:

            grouped_lines.append(current_line)

            current_line = [item]

        previous_y = current_y

    if current_line:

        grouped_lines.append(current_line)

    return grouped_lines


# =========================================================
# MERGE LINE TEXT
# =========================================================

def merge_line_text(line_items):

    sorted_line = sorted(

        line_items,

        key=lambda x: x["x"]

    )

    words = []

    for item in sorted_line:

        text = item.get("text", "").strip()

        if len(text) == 0:
            continue

        words.append(text)

    return " ".join(words)


# =========================================================
# RECONSTRUCT FULL PAGE OCR
# =========================================================

def reconstruct_full_page_ocr(

    ocr_results

):

    if len(ocr_results) == 0:

        return ""

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    ocr_results = remove_duplicate_tokens(

        ocr_results

    )

    grouped_lines = group_ocr_lines(

        ocr_results

    )

    reconstructed_lines = []

    for line in grouped_lines:

        merged_line = merge_line_text(

            line

        )

        if len(merged_line.strip()) == 0:
            continue

        print("\nLINE:")
        print(merged_line)
        
        reconstructed_lines.append(

            merged_line

        )

    return "\n".join(

        reconstructed_lines

    )


# =========================================================
# EXTRACT REGION TEXT
# =========================================================

def extract_region_text(region):

    region_type = region["type"]

    ocr_result = region["ocr"]

    # =====================================================
    # TABLE REGION
    # =====================================================

    if region_type.lower() == "table":

        table_text = []

        # ---------------------------------------------
        # HTML TABLES
        # ---------------------------------------------

        for table in ocr_result.get(

            "tables",
            []

        ):

            html = table.get(

                "html",
                ""

            )

            if len(html.strip()) > 0:

                table_text.append(html)

        # ---------------------------------------------
        # FALLBACK TEXT
        # ---------------------------------------------

        if len(table_text) == 0:

            table_text.append(

                ocr_result.get(

                    "text",
                    ""

                )

            )

        return "\n".join(table_text)

    # =====================================================
    # NORMAL REGION
    # =====================================================

    return ocr_result.get(

        "text",
        ""

    )


# =========================================================
# MERGE PAGE BLOCKS OCR
# =========================================================

def merge_page_blocks_ocr(

    region_outputs

):

    full_page_ocr_data = []

    for region in region_outputs:

        ocr_result = region["ocr"]

        region_type = region["type"]

        # =================================================
        # SKIP FIGURES
        # =================================================

        if region_type.lower() == "figure":

            continue

        # =================================================
        # COLLECT OCR TOKENS
        # =================================================

        for item in ocr_result.get(

            "ocr_data",
            []

        ):
        
            print(
                "OCR TOKENS:",
                len(
                    ocr_result.get(
                        "ocr_data",
                        []
                    )
                )
            )

            full_page_ocr_data.append(item)

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    full_page_ocr_data = remove_duplicate_tokens(

        full_page_ocr_data

    )

    # =====================================================
    # RECONSTRUCT PAGE
    # =====================================================

    reconstructed_page = reconstruct_full_page_ocr(

        full_page_ocr_data

    )

    return {

        "ocr_data": full_page_ocr_data,

        "text": reconstructed_page

    }


# =========================================================
# BUILD STRUCTURED DOCUMENT
# =========================================================

def build_structured_document(

    page_name,

    region_outputs,

    output_folder,

    fallback_ocr=None

):

    os.makedirs(

        output_folder,

        exist_ok=True

    )

    structured_regions = []

    parsed_tables = []

    full_page_ocr_data = []

    # =====================================================
    # PROCESS REGIONS
    # =====================================================

    for region in region_outputs:

        region_type = region["type"]

        image_path = region["image_path"]

        ocr_result = region["ocr"]

        region_text = extract_region_text(

            region

        )

        # =================================================
        # STRUCTURED REGION
        # =================================================

        structured_regions.append({

            "region_type": region_type,

            "image_path": image_path,

            "region_text": region_text,

            "metadata": ocr_result.get(

                "metadata",
                {}

            )

        })

        # =================================================
        # TABLE PARSING
        # =================================================

        if region_type.lower() == "table":

            print(

                f"\nProcessing Table → "
                f"{image_path}"

            )

            try:

                cells = detect_table_cells(

                    image_path

                )

                print(

                    f"Detected Cells: "
                    f"{len(cells)}"

                )

                structured_table = assign_ocr_to_cells(

                    cells,

                    ocr_result.get(

                        "ocr_data",
                        []

                    )

                )

                parsed_tables.append({

                    "table_image": image_path,

                    "total_cells": len(structured_table),

                    "cells": structured_table,

                    "html_tables": ocr_result.get(

                        "tables",
                        []

                    )

                })

            except Exception as e:

                print(

                    f"Table Parsing Error: {e}"

                )

        # =================================================
        # GLOBAL OCR
        # =================================================

        if region_type.lower() != "figure":

            for item in ocr_result.get(

                "ocr_data",
                []

            ):

                full_page_ocr_data.append(item)

    # =====================================================
    # FALLBACK OCR MERGE
    # =====================================================


    print("\nDEBUG FALLBACK OCR")
    print(type(fallback_ocr))

    if fallback_ocr:
        print(fallback_ocr.keys())

    if fallback_ocr is not None:

        print("\nMerging Fallback OCR")

        for item in fallback_ocr.get(

            "ocr_data",
            []

        ):

            full_page_ocr_data.append(item)

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    full_page_ocr_data = remove_duplicate_tokens(

        full_page_ocr_data

    )

    # =====================================================
    # FULL PAGE OCR
    # =====================================================

    full_page_ocr = reconstruct_full_page_ocr(

        full_page_ocr_data

    )

    # =====================================================
    # INDEX TOKENS
    # =====================================================

    indexed_tokens = []

    for idx, token in enumerate(full_page_ocr_data):

        token["token_id"] = idx + 1

        indexed_tokens.append(token)

    # =====================================================
    # GROUP TOKENS INTO ROWS
    # =====================================================

    grouped_rows = group_tokens_into_rows(

        indexed_tokens

    )

    # =====================================================
    # DETECT KEY VALUE PAIRS
    # =====================================================

    kv_pairs = map_key_values(
        indexed_tokens
    )

    print("\nDEBUG INDEXED TOKENS TYPE")
    print(type(indexed_tokens))

    print("\nDEBUG FIRST TOKEN")

    if indexed_tokens:
        print(indexed_tokens[0])
    else:
        print("NO TOKENS FOUND")

    # =====================================================
    # SEMANTIC NORMALIZATION
    # =====================================================

    normalized_kv_pairs = normalize_kv_pairs(

        kv_pairs

    )

    # =====================================================
    # PAGE BLOCK OCR
    # =====================================================

    page_blocks_ocr = merge_page_blocks_ocr(

        region_outputs

    )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    final_output = {

        "page": page_name,

        "structured_regions": structured_regions,

        "parsed_tables": parsed_tables,

        "indexed_tokens": indexed_tokens,

        "grouped_rows": grouped_rows,

        "kv_pairs": kv_pairs,

        "normalized_kv_pairs": normalized_kv_pairs,

        "full_page_ocr": {

            "text": full_page_ocr,

            "total_words": len(full_page_ocr_data)

        }

    }

    # =====================================================
    # SAVE JSON
    # =====================================================

    output_path = os.path.join(

        output_folder,

        f"{page_name}_final_structured.json"

    )

    with open(

        output_path,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            final_output,

            file,

            indent=4,

            ensure_ascii=False

        )

    print(

        f"\nStructured OCR Saved → "
        f"{output_path}"

    )

    return final_output