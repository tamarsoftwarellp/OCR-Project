import cv2
import numpy as np


# =========================================================
# REMOVE DUPLICATE CELLS
# =========================================================

def remove_duplicate_cells(

    cells,

    overlap_threshold=0.85

):

    filtered = []

    for cell in cells:

        x1 = cell["x"]
        y1 = cell["y"]

        x2 = x1 + cell["w"]
        y2 = y1 + cell["h"]

        is_duplicate = False

        for existing in filtered:

            ex1 = existing["x"]
            ey1 = existing["y"]

            ex2 = ex1 + existing["w"]
            ey2 = ey1 + existing["h"]

            # =================================================
            # INTERSECTION
            # =================================================

            ix1 = max(x1, ex1)
            iy1 = max(y1, ey1)

            ix2 = min(x2, ex2)
            iy2 = min(y2, ey2)

            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)

            intersection = iw * ih

            area1 = cell["w"] * cell["h"]
            area2 = existing["w"] * existing["h"]

            smaller_area = min(area1, area2)

            overlap_ratio = (

                intersection

                /

                (smaller_area + 1e-5)

            )

            if overlap_ratio > overlap_threshold:

                is_duplicate = True
                break

        if not is_duplicate:

            filtered.append(cell)

    return filtered


# =========================================================
# GROUP CELLS INTO ROWS
# =========================================================

def group_cells_into_rows(

    cells,

    y_threshold=25

):

    if len(cells) == 0:

        return []

    cells = sorted(

        cells,

        key=lambda x: (

            x["y"],
            x["x"]

        )

    )

    rows = []

    current_row = [cells[0]]

    previous_y = cells[0]["y"]

    for cell in cells[1:]:

        current_y = cell["y"]

        if abs(current_y - previous_y) <= y_threshold:

            current_row.append(cell)

        else:

            rows.append(

                sorted(

                    current_row,

                    key=lambda x: x["x"]

                )

            )

            current_row = [cell]

        previous_y = current_y

    if current_row:

        rows.append(

            sorted(

                current_row,

                key=lambda x: x["x"]

            )

        )

    return rows


# =========================================================
# DETECT TABLE CELLS
# =========================================================

def detect_table_cells(image_path):

    image = cv2.imread(image_path)

    if image is None:

        return []

    gray = cv2.cvtColor(

        image,

        cv2.COLOR_BGR2GRAY

    )

    # =====================================================
    # BINARIZATION
    # =====================================================

    binary = cv2.adaptiveThreshold(

        ~gray,

        255,

        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,

        cv2.THRESH_BINARY,

        15,

        -10

    )

    # =====================================================
    # HORIZONTAL LINES
    # =====================================================

    horizontal = binary.copy()

    cols = horizontal.shape[1]

    horizontal_size = max(

        40,

        cols // 20

    )

    horizontal_structure = cv2.getStructuringElement(

        cv2.MORPH_RECT,

        (horizontal_size, 1)

    )

    horizontal = cv2.erode(

        horizontal,

        horizontal_structure

    )

    horizontal = cv2.dilate(

        horizontal,

        horizontal_structure

    )

    # =====================================================
    # VERTICAL LINES
    # =====================================================

    vertical = binary.copy()

    rows = vertical.shape[0]

    vertical_size = max(

        40,

        rows // 20

    )

    vertical_structure = cv2.getStructuringElement(

        cv2.MORPH_RECT,

        (1, vertical_size)

    )

    vertical = cv2.erode(

        vertical,

        vertical_structure

    )

    vertical = cv2.dilate(

        vertical,

        vertical_structure

    )

    # =====================================================
    # TABLE MASK
    # =====================================================

    table_mask = cv2.add(

        horizontal,

        vertical

    )

    # =====================================================
    # CLOSE GAPS
    # =====================================================

    kernel = cv2.getStructuringElement(

        cv2.MORPH_RECT,

        (3, 3)

    )

    table_mask = cv2.morphologyEx(

        table_mask,

        cv2.MORPH_CLOSE,

        kernel,

        iterations=2

    )

    # =====================================================
    # FIND CONTOURS
    # =====================================================

    contours, hierarchy = cv2.findContours(

        table_mask,

        cv2.RETR_TREE,

        cv2.CHAIN_APPROX_SIMPLE

    )

    cells = []

    image_h, image_w = image.shape[:2]

    image_area = image_h * image_w

    for cnt in contours:

        x, y, w, h = cv2.boundingRect(cnt)

        area = w * h

        # =================================================
        # FILTERS
        # =================================================

        if w < 35:
            continue

        if h < 18:
            continue

        if area < 400:
            continue

        if area > image_area * 0.90:
            continue

        # =================================================
        # THIN LINES
        # =================================================

        if w > image_w * 0.95 and h < 20:
            continue

        if h > image_h * 0.95 and w < 20:
            continue

        # =================================================
        # ASPECT RATIO
        # =================================================

        aspect_ratio = w / float(h)

        if aspect_ratio > 30:
            continue

        cells.append({

            "x": x,
            "y": y,

            "w": w,
            "h": h

        })

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    cells = remove_duplicate_cells(

        cells

    )

    # =====================================================
    # SORT CELLS
    # =====================================================

    cells = sorted(

        cells,

        key=lambda c: (

            c["y"],
            c["x"]

        )

    )

    return cells


# =========================================================
# OCR INSIDE CELL
# =========================================================

def get_ocr_inside_cell(

    cell,

    ocr_data

):

    x1 = cell["x"]
    y1 = cell["y"]

    x2 = x1 + cell["w"]
    y2 = y1 + cell["h"]

    matched = []

    for item in ocr_data:

        cx = item["center_x"]
        cy = item["center_y"]

        # =================================================
        # CENTER INSIDE CELL
        # =================================================

        if (

            x1 <= cx <= x2

            and

            y1 <= cy <= y2

        ):

            matched.append(item)

    # =====================================================
    # SORT
    # =====================================================

    matched = sorted(

        matched,

        key=lambda x: (

            x["y"],
            x["x"]

        )

    )

    return matched


# =========================================================
# REMOVE DUPLICATE OCR WORDS
# =========================================================

def remove_duplicate_ocr_words(ocr_items):

    unique = []

    seen = set()

    for item in ocr_items:

        text = item["text"].strip().lower()

        x = round(item["x"] / 5)
        y = round(item["y"] / 5)

        key = (text, x, y)

        if key in seen:
            continue

        seen.add(key)

        unique.append(item)

    return unique


# =========================================================
# MERGE OCR TEXT
# =========================================================

def merge_ocr_text(

    ocr_items

):

    ocr_items = remove_duplicate_ocr_words(

        ocr_items

    )

    texts = []

    for item in ocr_items:

        text = item["text"].strip()

        if len(text) == 0:
            continue

        texts.append(text)

    return " ".join(texts)


# =========================================================
# ASSIGN OCR TO CELLS
# =========================================================

def assign_ocr_to_cells(

    cells,

    ocr_data

):

    structured_cells = []

    rows = group_cells_into_rows(

        cells

    )

    for row_idx, row_cells in enumerate(rows):

        for col_idx, cell in enumerate(row_cells):

            ocr_inside = get_ocr_inside_cell(

                cell,

                ocr_data

            )

            merged_text = merge_ocr_text(

                ocr_inside

            )

            x1 = cell["x"]
            y1 = cell["y"]

            x2 = x1 + cell["w"]
            y2 = y1 + cell["h"]

            structured_cells.append({

                "row": row_idx,

                "column": col_idx,

                "cell": {

                    "x1": x1,
                    "y1": y1,

                    "x2": x2,
                    "y2": y2,

                    "width": cell["w"],
                    "height": cell["h"]

                },

                "text": merged_text,

                "is_empty":

                    len(merged_text.strip()) == 0

            })

    return structured_cells