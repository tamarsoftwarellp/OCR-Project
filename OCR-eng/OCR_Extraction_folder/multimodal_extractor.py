from paddleocr import PaddleOCR

import time
import numpy as np
import os
import json


# =========================================================
# OCR ENGINE SINGLETON
# =========================================================

ocr_engine = None


# =========================================================
# LOAD PADDLE OCR
# =========================================================

def load_paddleocr():

    global ocr_engine

    if ocr_engine is None:

        print("Loading PaddleOCR Model...")

        ocr_engine = PaddleOCR(

        use_angle_cls=True,

        lang='en',

        use_gpu=False,

        show_log=False,

        det_db_box_thresh=0.2,

        det_db_thresh=0.2,

        det_limit_side_len=2000,

        rec_batch_num=8,

        use_dilation=True

    )

    return ocr_engine


# =========================================================
# SPECIAL SYMBOL NORMALIZATION
# =========================================================

import re


# =========================================================
# SPECIAL SYMBOL NORMALIZATION
# =========================================================

SPECIAL_SYMBOL_MAP = {

    "=<": "≤",
    "=>": "≥",

    "<=": "≤",
    ">=": "≥",

    "<<": "«",
    ">>": "»",

    "[v]": "☑",
    "(v)": "☑",

    "[ ]": "☐",
    "( )": "☐",

    "¥": "₹"
}


# =========================================================
# SUPERSCRIPT CONVERTER
# =========================================================

SUPERSCRIPT_MAP = {

    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹"
}


def to_superscript(number):

    return "".join(

        SUPERSCRIPT_MAP.get(ch, ch)

        for ch in str(number)
    )


# =========================================================
# NORMALIZE SYMBOLS
# =========================================================

# =========================================================
# NORMALIZE SPECIAL SYMBOLS
# =========================================================

def normalize_special_symbols(text):

    if not text:
        return ""

    text = text.strip()

    # =====================================================
    # DIRECT REPLACEMENTS
    # =====================================================

    for wrong, correct in SPECIAL_SYMBOL_MAP.items():

        text = text.replace(
            wrong,
            correct
        )

    # =====================================================
    # FIX <= >=
    # =====================================================

    text = re.sub(r'<\s*=', '≤', text)

    text = re.sub(r'>\s*=', '≥', text)

    # =====================================================
    # FIX NMT / NLT
    # =====================================================

    # NMT 140 -> ≤140

    text = re.sub(

        r'\bNMT\s+(\d+)',

        r'≤\1',

        text,

        flags=re.IGNORECASE
    )

    # NLT 25 -> ≥25

    text = re.sub(

        r'\bNLT\s+(\d+)',

        r'≥\1',

        text,

        flags=re.IGNORECASE
    )

    # LT 10 -> <10

    text = re.sub(

        r'\bLT\s+(\d+)',

        r'<\1',

        text,

        flags=re.IGNORECASE
    )

    # GT 50 -> >50

    text = re.sub(

        r'\bGT\s+(\d+)',

        r'>\1',

        text,

        flags=re.IGNORECASE
    )

    # =====================================================
    # FIX SCIENTIFIC NOTATION
    # =====================================================

    # 103 -> 10³

    text = re.sub(

        r'\b10([0-9])\b',

        lambda m:
            f"10{to_superscript(m.group(1))}",

        text
    )

    # =====================================================
    # FIX CFU PATTERNS
    # =====================================================

    text = re.sub(

        r'\b10³\s*(cfu/ml)\b',

        r'≤10³ \1',

        text,

        flags=re.IGNORECASE
    )

    text = re.sub(

        r'\b10²\s*(cfu/ml)\b',

        r'≤10² \1',

        text,

        flags=re.IGNORECASE
    )

    text = re.sub(

        r'\b10⁴\s*(cfu/ml)\b',

        r'≤10⁴ \1',

        text,

        flags=re.IGNORECASE
    )

    # =====================================================
    # FIX OCR PERCENT ISSUES
    # =====================================================

    text = re.sub(r'\bO\/O\b', '%', text)

    text = re.sub(r'\b0\/0\b', '%', text)

    # =====================================================
    # FIX PLUS / MINUS
    # =====================================================

    text = re.sub(

        r'\bplus\b',

        '+',

        text,

        flags=re.IGNORECASE
    )

    text = re.sub(

        r'\bminus\b',

        '-',

        text,

        flags=re.IGNORECASE
    )

    # +/- -> ±

    text = re.sub(

        r'\+\/-',

        '±',

        text
    )

    # =====================================================
    # PRESERVE < >
    # =====================================================

    text = re.sub(r'\s<\s', ' < ', text)

    text = re.sub(r'\s>\s', ' > ', text)

    # =====================================================
    # PRESERVE MULTIPLE UNDERSCORES
    # =====================================================

    text = re.sub(

        r'_{2,}',

        '_____',

        text
    )

    # =====================================================
    # FIX OCR NOISE BEFORE SYMBOLS
    # =====================================================

    text = re.sub(r'\|\<', '<', text)

    text = re.sub(r'\|\>', '>', text)

    text = re.sub(r'1\<', '<', text)

    text = re.sub(r'1\>', '>', text)

    # =====================================================
    # REMOVE RANDOM DOUBLE SPACES
    # =====================================================

    text = re.sub(

        r'[ \t]+',

        ' ',

        text
    )

    return text.strip()





# =========================================================
# SORT TOKENS
# =========================================================

def sort_tokens(tokens):

    """
    Sort tokens top-to-bottom then left-to-right
    """

    return sorted(

        tokens,

        key=lambda x: (

            x["y"],
            x["x"]

        )
    )



# =========================================================
# COLUMN DETECTION
# =========================================================

def detect_columns(tokens, tolerance=40):

    columns = []

    for token in tokens:

        x = token["x"]

        matched = False

        for col in columns:

            if abs(col["x"] - x) < tolerance:

                col["tokens"].append(token)

                matched = True

                break

        if not matched:

            columns.append({

                "x": x,

                "tokens": [token]
            })

    return sorted(

        columns,

        key=lambda c: c["x"]
    )



# =========================================================
# BUILD TABLE ROWS
# =========================================================

def build_table_rows(

    tokens,

    y_threshold=20

):

    if not tokens:

        return []

    # =====================================================
    # SORT TOKENS
    # =====================================================

    tokens = sorted(

        tokens,

        key=lambda t: (

            t["y"],
            t["x"]
        )
    )

    rows = []

    current_row = []

    current_y = None

    # =====================================================
    # GROUP BY Y POSITION
    # =====================================================

    for token in tokens:

        if current_y is None:

            current_row.append(token)

            current_y = token["y"]

            continue

        # SAME ROW

        if abs(token["y"] - current_y) <= y_threshold:

            current_row.append(token)

        else:

            rows.append(current_row)

            current_row = [token]

            current_y = token["y"]

    if current_row:

        rows.append(current_row)

    # =====================================================
    # SORT INSIDE ROW
    # =====================================================

    structured_rows = []

    row_id = 1

    for row in rows:

        row = sorted(

            row,

            key=lambda t: t["x"]
        )

        structured_rows.append({

            "row_id": row_id,

            "cells": [

                token["text"]

                for token in row
            ],

            "tokens": row
        })

        row_id += 1

    return structured_rows


# =========================================================
# LIGHT LINE GROUPING
# =========================================================

def build_lines(tokens, y_threshold=18):

    """
    Group nearby tokens into lightweight lines
    """

    if not tokens:

        return [], ""

    sorted_tokens = sort_tokens(tokens)

    rows = []

    current_row = []

    current_y = None

    # =====================================================
    # BUILD ROWS
    # =====================================================

    for token in sorted_tokens:

        if current_y is None:

            current_row.append(token)

            current_y = token["y"]

            continue

        # SAME LINE

        if abs(token["y"] - current_y) <= y_threshold:

            current_row.append(token)

        else:

            rows.append(current_row)

            current_row = [token]

            current_y = token["y"]

    if current_row:

        rows.append(current_row)

    # =====================================================
    # BUILD LINE STRUCTURE
    # =====================================================

    lines = []

    full_text_lines = []

    line_id = 1

    for row in rows:

        row = sorted(
            row,
            key=lambda x: x["x"]
        )

        line_text = " ".join([

            token["text"]

            for token in row

        ])

        token_ids = [

            token["token_id"]

            for token in row

        ]

        lines.append({

            "line_id": line_id,

            "text": line_text,

            "token_ids": token_ids

        })

        full_text_lines.append(
            line_text
        )

        line_id += 1

    full_text = "\n".join(
        full_text_lines
    )

    return lines, full_text


# =========================================================
# SAVE OCR OUTPUTS
# =========================================================

def save_ocr_outputs(

    image_path,
    output_folder,
    final_output

):

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    base_name = os.path.splitext(

        os.path.basename(image_path)

    )[0]

    # =====================================================
    # RAW TEXT
    # =====================================================

    raw_text_path = os.path.join(

        output_folder,

        f"{base_name}_raw.txt"

    )

    with open(

        raw_text_path,

        "w",

        encoding="utf-8"

    ) as file:

        file.write(
            final_output["full_text"]
        )

    # =====================================================
    # FINAL JSON
    # =====================================================

    json_path = os.path.join(

        output_folder,

        f"{base_name}_ocr.json"

    )

    with open(

        json_path,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            final_output,

            file,

            indent=4,

            ensure_ascii=False

        )

    print(f"OCR Raw Text Saved → {raw_text_path}")

    print(f"OCR JSON Saved → {json_path}")


# =========================================================
# OCR EXTRACTION
# =========================================================

def extract_with_paddle(image_path):

    engine = load_paddleocr()

    start_time = time.time()

    result = engine.ocr(image_path)

    processing_time = round(

        time.time() - start_time,

        2

    )

    # =====================================================
    # EMPTY RESULT
    # =====================================================

    if not result or result[0] is None:

        return {

            "tokens": [],

            "lines": [],

            "full_text": "",

            "metadata": {

                "engine": "PaddleOCR",

                "processing_time": processing_time,

                "total_tokens": 0,

                "total_lines": 0,

                "avg_confidence": 0
            }
        }

    tokens = []

    confidence_scores = []

    token_id = 1

    # =====================================================
    # EXTRACT TOKENS
    # =====================================================

    for line in result[0]:

        try:

            bbox = line[0]

            raw_text = line[1][0]

            confidence = float(line[1][1])

            # =================================================
            # LOWER THRESHOLD FOR SYMBOLS
            # =================================================

            if confidence < 0.30:

                continue

            text = normalize_special_symbols(
                raw_text
            )

            if len(text.strip()) < 1:

                continue

            confidence_scores.append(
                confidence
            )

            # =================================================
            # BBOX PROCESSING
            # =================================================

            x_coords = [p[0] for p in bbox]

            y_coords = [p[1] for p in bbox]

            x_min = int(min(x_coords))

            x_max = int(max(x_coords))

            y_min = int(min(y_coords))

            y_max = int(max(y_coords))

            width = x_max - x_min

            height = y_max - y_min

            center_x = x_min + width // 2

            center_y = y_min + height // 2

            # =================================================
            # TOKEN OBJECT
            # =================================================

            token_object = {

                "token_id": token_id,

                "text": text,

                "confidence": round(
                    confidence,
                    3
                ),

                "bbox": bbox,

                "x": x_min,
                "y": y_min,

                "x2": x_max,
                "y2": y_max,

                "width": width,
                "height": height,

                "center_x": center_x,
                "center_y": center_y
            }

            tokens.append(
                token_object
            )

            token_id += 1

        except Exception as e:

            print(f"OCR Parsing Error: {e}")

            continue

    # =====================================================
    # SORT TOKENS
    # =====================================================

    tokens = sort_tokens(tokens)


    # =====================================================
    # COLUMN DETECTION
    # =====================================================

    columns = detect_columns(tokens)

    print(f"Detected Columns: {len(columns)}")



    # =====================================================
    # BUILD TABLE ROWS
    # =====================================================

    table_rows = build_table_rows(tokens)

    print(f"Detected Rows: {len(table_rows)}")


    # =====================================================
    # BUILD LIGHT LINES
    # =====================================================

    lines, full_text = build_lines(
        tokens
    )

    # =====================================================
    # METADATA
    # =====================================================

    avg_confidence = 0

    if confidence_scores:

        avg_confidence = round(

            np.mean(confidence_scores),

            3

        )

    metadata = {

        "engine": "PaddleOCR",

        "processing_time": processing_time,

        "total_tokens": len(tokens),

        "total_lines": len(lines),

        "avg_confidence": avg_confidence
    }

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    return {

    # =================================================
    # NEW FORMAT
    # =================================================

        "tokens": tokens,

        "columns": columns,

        "table_rows": table_rows,

        "lines": lines,

        "full_text": full_text,

        "metadata": metadata,

        # =================================================
        # BACKWARD COMPATIBILITY
        # =================================================

        "ocr_data": tokens,

        "text": full_text
    }


# =========================================================
# MAIN OCR PIPELINE
# =========================================================

def multimodal_extract(

    image_path,
    output_folder=None

):

    print(f"\nRunning OCR → {image_path}")

    ocr_result = extract_with_paddle(
        image_path
    )

    # =====================================================
    # SAVE OUTPUTS
    # =====================================================

    if output_folder is not None:

        save_ocr_outputs(

            image_path=image_path,

            output_folder=output_folder,

            final_output=ocr_result

        )

    return ocr_result