# import layoutparser as lp
# import cv2
# import os
# import json


# # =========================================================
# # LOAD MODEL
# # =========================================================

# import layoutparser as lp


# # =========================================================
# # LOAD MODEL
# # =========================================================

# import layoutparser as lp

# import cv2
# import os
# import json


# # =========================================================
# # LOAD LAYOUT MODEL
# # =========================================================

# model = lp.PaddleDetectionLayoutModel(

#     config_path=

#     "lp://PubLayNet/ppyolov2_r50vd_dcn_365e/config",

#     label_map={

#         0: "Text",

#         1: "Title",

#         2: "List",

#         3: "Table",

#         4: "Figure"

#     }

# )


# # =========================================================
# # IOU CALCULATION
# # =========================================================

# def calculate_iou(boxA, boxB):

#     xA = max(boxA[0], boxB[0])
#     yA = max(boxA[1], boxB[1])

#     xB = min(boxA[2], boxB[2])
#     yB = min(boxA[3], boxB[3])

#     inter_area = max(0, xB - xA) * max(0, yB - yA)

#     if inter_area == 0:
#         return 0

#     boxA_area = (
#         (boxA[2] - boxA[0]) *
#         (boxA[3] - boxA[1])
#     )

#     boxB_area = (
#         (boxB[2] - boxB[0]) *
#         (boxB[3] - boxB[1])
#     )

#     return inter_area / float(
#         boxA_area + boxB_area - inter_area
#     )


# # =========================================================
# # REMOVE DUPLICATE BLOCKS
# # =========================================================

# def remove_overlapping_blocks(blocks):

#     final_blocks = []

#     for block in blocks:

#         keep = True

#         boxA = [

#             int(block.block.x_1),
#             int(block.block.y_1),
#             int(block.block.x_2),
#             int(block.block.y_2)

#         ]

#         for saved in final_blocks:

#             boxB = [

#                 int(saved.block.x_1),
#                 int(saved.block.y_1),
#                 int(saved.block.x_2),
#                 int(saved.block.y_2)

#             ]

#             iou = calculate_iou(boxA, boxB)

#             if iou > 0.70:

#                 keep = False
#                 break

#         if keep:
#             final_blocks.append(block)

#     return final_blocks


# # =========================================================
# # SAVE REGION
# # =========================================================

# def save_region(

#     image,
#     block,
#     output_folder,
#     page_name,
#     region_id,
#     region_type

# ):

#     padding = 15

#     x1 = int(block.block.x_1) - padding
#     y1 = int(block.block.y_1) - padding

#     x2 = int(block.block.x_2) + padding
#     y2 = int(block.block.y_2) + padding

#     image_h, image_w = image.shape[:2]

#     x1 = max(0, x1)
#     y1 = max(0, y1)

#     x2 = min(image_w, x2)
#     y2 = min(image_h, y2)

#     if x2 <= x1 or y2 <= y1:
#         return None

#     cropped = image[y1:y2, x1:x2]

#     if cropped.size == 0:
#         return None

#     h, w = cropped.shape[:2]

#     if h < 25 or w < 25:
#         return None

#     region_filename = (

#         f"{page_name}_"
#         f"region_{region_id}_"
#         f"{region_type}.png"

#     )

#     region_path = os.path.join(

#         output_folder,
#         region_filename

#     )

#     success = cv2.imwrite(
#         region_path,
#         cropped
#     )

#     if not success:
#         return None

#     return region_path


# # =========================================================
# # SORT READING ORDER
# # =========================================================

# def sort_layout_blocks(blocks):

#     return sorted(

#         blocks,

#         key=lambda b: (

#             round(b.block.y_1 / 50),

#             b.block.x_1

#         )

#     )


# # =========================================================
# # MAIN DETECTOR
# # =========================================================

# def detect_layout(

#     image_path,
#     layout_output_folder,
#     cropped_output_folder

# ):

#     os.makedirs(
#         layout_output_folder,
#         exist_ok=True
#     )

#     os.makedirs(
#         cropped_output_folder,
#         exist_ok=True
#     )

#     image = cv2.imread(image_path)

#     if image is None:

#         raise ValueError(
#             f"Cannot read image: {image_path}"
#         )

#     print(f"\nRunning Layout Detection → {image_path}")

#     # =====================================================
#     # DETECT
#     # =====================================================

#     layout = model.detect(image)

#     print(f"Detected Raw Blocks: {len(layout)}")

#     # =====================================================
#     # FILTERING
#     # =====================================================

#     allowed_types = [

#         "Text",
#         "Title",
#         "List",
#         "Table"

#     ]

#     image_h, image_w = image.shape[:2]

#     filtered_layout = []

#     for block in layout:

#         region_type = str(block.type)

#         score = float(block.score)

#         if region_type not in allowed_types:
#             continue

#         if score < 0.35:
#             continue

#         x1 = int(block.block.x_1)
#         y1 = int(block.block.y_1)

#         x2 = int(block.block.x_2)
#         y2 = int(block.block.y_2)

#         width = x2 - x1
#         height = y2 - y1

#         if width < 20 or height < 20:
#             continue

#         coverage = (

#             (width * height)

#             /

#             (image_w * image_h)

#         )

#         if coverage > 0.95:
#             continue

#         filtered_layout.append(block)

#     # =====================================================
#     # REMOVE OVERLAPS
#     # =====================================================

#     filtered_layout = remove_overlapping_blocks(
#         filtered_layout
#     )

#     # =====================================================
#     # SORT BLOCKS
#     # =====================================================

#     filtered_layout = sort_layout_blocks(
#         filtered_layout
#     )

#     print(
#         f"Final Layout Blocks: {len(filtered_layout)}"
#     )

#     # =====================================================
#     # VISUALIZATION
#     # =====================================================

#     visualized = image.copy()

#     color_map = {

#         "Text": (0, 255, 0),
#         "Title": (255, 0, 0),
#         "List": (0, 255, 255),
#         "Table": (0, 0, 255)

#     }

#     layout_json = []
#     cropped_regions = []

#     page_name = os.path.splitext(

#         os.path.basename(image_path)

#     )[0]

#     # =====================================================
#     # PROCESS BLOCKS
#     # =====================================================

#     for idx, block in enumerate(filtered_layout):

#         region_type = str(block.type)

#         score = round(float(block.score), 3)

#         x1 = int(block.block.x_1)
#         y1 = int(block.block.y_1)

#         x2 = int(block.block.x_2)
#         y2 = int(block.block.y_2)

#         # =================================================
#         # DRAW
#         # =================================================

#         cv2.rectangle(

#             visualized,

#             (x1, y1),
#             (x2, y2),

#             color_map.get(
#                 region_type,
#                 (255, 255, 255)
#             ),

#             3

#         )

#         cv2.putText(

#             visualized,

#             f"{region_type}",

#             (x1, y1 - 10),

#             cv2.FONT_HERSHEY_SIMPLEX,

#             0.7,

#             color_map.get(
#                 region_type,
#                 (255, 255, 255)
#             ),

#             2

#         )

#         # =================================================
#         # SAVE CROPS
#         # =================================================

#         region_path = save_region(

#             image=image,

#             block=block,

#             output_folder=cropped_output_folder,

#             page_name=page_name,

#             region_id=idx + 1,

#             region_type=region_type

#         )

#         if region_path is None:
#             continue

#         cropped_regions.append({

#             "region_id": idx + 1,

#             "type": region_type,

#             "path": region_path

#         })

#         layout_json.append({

#             "region_id": idx + 1,

#             "type": region_type,

#             "score": score,

#             "bbox": {

#                 "x1": x1,
#                 "y1": y1,

#                 "x2": x2,
#                 "y2": y2

#             },

#             "cropped_region": region_path

#         })

#     # =====================================================
#     # SAVE VISUALIZATION
#     # =====================================================

#     layout_image_path = os.path.join(

#         layout_output_folder,

#         f"{page_name}_layout.png"

#     )

#     cv2.imwrite(
#         layout_image_path,
#         visualized
#     )

#     # =====================================================
#     # SAVE JSON
#     # =====================================================

#     json_path = os.path.join(

#         layout_output_folder,

#         f"{page_name}_layout.json"

#     )

#     with open(

#         json_path,
#         "w",
#         encoding="utf-8"

#     ) as file:

#         json.dump(

#             layout_json,

#             file,

#             indent=4,

#             ensure_ascii=False

#         )

#     print(f"Layout JSON Saved → {json_path}")

#     print(
#         f"Total Cropped Regions → "
#         f"{len(cropped_regions)}"
#     )

#     return {

#         "layout_data": layout_json,

#         "cropped_regions": cropped_regions,

#         "layout_image": layout_image_path

#     }




# layout_block_detection.py

import cv2
import os
import json
from doclayout_yolo import YOLOv10


# =========================================================
# DOCLAYOUT-YOLO LABEL MAP
# =========================================================

LABEL_MAP = {
    0: "title",
    1: "plain text",
    2: "abandon",
    3: "figure",
    4: "figure_caption",
    5: "table",
    6: "table_caption",
    7: "table_footnote",
    8: "isolate_formula",
    9: "formula_caption"
}

# Allowed region types to keep
ALLOWED_TYPES = {
    "title",
    "plain text",
    "table",
    "figure"
}

# Color map for visualization
COLOR_MAP = {
    "title":      (255, 0, 0),
    "plain text": (0, 255, 0),
    "table":      (0, 0, 255),
    "figure":     (0, 255, 255)
}


# =========================================================
# LOAD MODEL — SINGLETON
# =========================================================

_model = None


def load_model():

    global _model

    if _model is None:

        print("Loading DocLayout-YOLO Model...")

        _model = YOLOv10("models/doclayout_yolo_docstructbench_imgsz1024.pt")

        print("DocLayout-YOLO Model Loaded.")

    return _model


# =========================================================
# IOU CALCULATION
# =========================================================

def calculate_iou(boxA, boxB):

    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_area = max(0, xB - xA) * max(0, yB - yA)

    if inter_area == 0:
        return 0

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    return inter_area / float(boxA_area + boxB_area - inter_area)


# =========================================================
# REMOVE OVERLAPPING BLOCKS
# =========================================================

def remove_overlapping_blocks(blocks, iou_threshold=0.70):

    final_blocks = []

    for block in blocks:

        keep = True
        boxA = block["bbox_list"]

        for saved in final_blocks:

            boxB = saved["bbox_list"]
            iou  = calculate_iou(boxA, boxB)

            if iou > iou_threshold:
                keep = False
                break

        if keep:
            final_blocks.append(block)

    return final_blocks


# =========================================================
# SORT BLOCKS IN READING ORDER
# Top-to-bottom, left-to-right with row snapping
# =========================================================

def sort_layout_blocks(blocks):

    return sorted(
        blocks,
        key=lambda b: (
            round(b["y1"] / 50),
            b["x1"]
        )
    )


# =========================================================
# SAVE CROPPED REGION
# =========================================================

def save_region(
    image,
    x1, y1, x2, y2,
    output_folder,
    page_name,
    region_id,
    region_type,
    padding=15
):

    image_h, image_w = image.shape[:2]

    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(image_w, x2 + padding)
    y2 = min(image_h, y2 + padding)

    if x2 <= x1 or y2 <= y1:
        return None

    cropped = image[y1:y2, x1:x2]

    if cropped.size == 0:
        return None

    h, w = cropped.shape[:2]

    if h < 25 or w < 25:
        return None

    filename = (
        f"{page_name}_"
        f"region_{region_id}_"
        f"{region_type}.png"
    )

    region_path = os.path.join(output_folder, filename)

    success = cv2.imwrite(region_path, cropped)

    if not success:
        return None

    return region_path


# =========================================================
# PARSE DETECTIONS
# Converts raw YOLO result boxes into clean block dicts
# =========================================================

def parse_detections(result, image_w, image_h, conf_threshold=0.35):

    image_area = image_w * image_h

    blocks = []

    for box in result.boxes:

        cls_id = int(box.cls[0])
        score  = float(box.conf[0])

        region_type = LABEL_MAP.get(cls_id, "unknown")

        # -------------------------------------------------
        # FILTER BY TYPE AND CONFIDENCE
        # -------------------------------------------------

        if region_type not in ALLOWED_TYPES:
            continue

        if score < conf_threshold:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        width  = x2 - x1
        height = y2 - y1

        if width < 20 or height < 20:
            continue

        coverage = (width * height) / image_area

        if coverage > 0.95:
            continue

        blocks.append({
            "type":      region_type,
            "score":     round(score, 3),
            "x1":        x1,
            "y1":        y1,
            "x2":        x2,
            "y2":        y2,
            "bbox_list": [x1, y1, x2, y2]
        })

    return blocks


# =========================================================
# MAIN LAYOUT DETECTOR
# =========================================================

def detect_layout(
    image_path,
    layout_output_folder,
    cropped_output_folder,
    conf_threshold=0.35,
    imgsz=1024
):

    os.makedirs(layout_output_folder, exist_ok=True)
    os.makedirs(cropped_output_folder, exist_ok=True)

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    image_h, image_w = image.shape[:2]

    print(f"\nRunning Layout Detection → {image_path}")

    # =====================================================
    # DETECT
    # =====================================================

    model = load_model()

    results = model.predict(
        image,
        imgsz=imgsz,
        conf=conf_threshold
    )

    result = results[0]

    print(f"Raw Detections: {len(result.boxes)}")

    # =====================================================
    # PARSE DETECTIONS
    # =====================================================

    blocks = parse_detections(
        result,
        image_w,
        image_h,
        conf_threshold=conf_threshold
    )

    # =====================================================
    # REMOVE OVERLAPS
    # =====================================================

    blocks = remove_overlapping_blocks(blocks)

    # =====================================================
    # SORT READING ORDER
    # =====================================================

    blocks = sort_layout_blocks(blocks)

    print(f"Final Layout Blocks: {len(blocks)}")

    # =====================================================
    # PROCESS BLOCKS
    # =====================================================

    page_name       = os.path.splitext(os.path.basename(image_path))[0]
    visualized      = image.copy()
    layout_json     = []
    cropped_regions = []

    for idx, block in enumerate(blocks):

        region_type = block["type"]
        score       = block["score"]
        x1          = block["x1"]
        y1          = block["y1"]
        x2          = block["x2"]
        y2          = block["y2"]
        region_id   = idx + 1

        # -------------------------------------------------
        # DRAW VISUALIZATION
        # -------------------------------------------------

        color = COLOR_MAP.get(region_type, (255, 255, 255))

        cv2.rectangle(visualized, (x1, y1), (x2, y2), color, 3)

        cv2.putText(
            visualized,
            f"{region_type} {score:.2f}",
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

        # -------------------------------------------------
        # SAVE CROP
        # -------------------------------------------------

        region_path = save_region(
            image=image,
            x1=x1, y1=y1, x2=x2, y2=y2,
            output_folder=cropped_output_folder,
            page_name=page_name,
            region_id=region_id,
            region_type=region_type
        )

        if region_path is None:
            continue

        cropped_regions.append({
            "region_id": region_id,
            "type":      region_type,
            "path":      region_path
        })

        layout_json.append({
            "region_id":      region_id,
            "type":           region_type,
            "score":          score,
            "bbox": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            },
            "cropped_region": region_path
        })

    # =====================================================
    # SAVE VISUALIZATION
    # =====================================================

    layout_image_path = os.path.join(
        layout_output_folder,
        f"{page_name}_layout.png"
    )

    cv2.imwrite(layout_image_path, visualized)

    # =====================================================
    # SAVE JSON
    # =====================================================

    json_path = os.path.join(
        layout_output_folder,
        f"{page_name}_layout.json"
    )

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(layout_json, f, indent=4, ensure_ascii=False)

    print(f"Layout JSON Saved     → {json_path}")
    print(f"Total Cropped Regions → {len(cropped_regions)}")

    return {
        "layout_data":     layout_json,
        "cropped_regions": cropped_regions,
        "layout_image":    layout_image_path
    }