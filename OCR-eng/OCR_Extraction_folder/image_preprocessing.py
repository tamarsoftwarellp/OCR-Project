import cv2
import numpy as np
import os


# =========================================================
# IMAGE QUALITY ANALYSIS
# =========================================================

def analyze_image(gray):

    blur_score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    contrast_score = gray.std()

    brightness_score = gray.mean()

    return {

        "blur": blur_score,

        "contrast": contrast_score,

        "brightness": brightness_score

    }


# =========================================================
# SAFE DESKEW
# =========================================================

def safe_deskew(image):

    thresh = cv2.threshold(

        image,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU

    )[1]

    coords = np.column_stack(

        np.where(thresh > 0)

    )

    if len(coords) < 100:

        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:

        angle += 90

    if abs(angle) < 1:

        return image

    if abs(angle) > 15:

        return image

    h, w = image.shape

    center = (w // 2, h // 2)

    matrix = cv2.getRotationMatrix2D(

        center,
        angle,
        1.0

    )

    rotated = cv2.warpAffine(

        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE

    )

    print(f"Deskew Applied → {angle:.2f}")

    return rotated


# =========================================================
# SHADOW REMOVAL
# =========================================================

def remove_shadows(gray):

    dilated = cv2.dilate(

        gray,
        np.ones((7, 7), np.uint8)

    )

    background = cv2.medianBlur(

        dilated,
        21

    )

    diff = 255 - cv2.absdiff(

        gray,
        background

    )

    normalized = cv2.normalize(

        diff,
        None,
        0,
        255,
        cv2.NORM_MINMAX

    )

    return normalized


# =========================================================
# NORMALIZE BRIGHTNESS
# =========================================================

def normalize_brightness(image):

    return cv2.normalize(

        image,
        None,
        0,
        255,
        cv2.NORM_MINMAX

    )


# =========================================================
# MORPHOLOGICAL CLEANUP
# =========================================================

def morphological_cleanup(image):

    kernel = np.ones((2, 2), np.uint8)

    opened = cv2.morphologyEx(

        image,
        cv2.MORPH_OPEN,
        kernel

    )

    cleaned = cv2.morphologyEx(

        opened,
        cv2.MORPH_CLOSE,
        kernel

    )

    return cleaned


# =========================================================
# DYNAMIC THRESHOLD
# =========================================================

def dynamic_threshold(image, contrast_score):

    if contrast_score > 50:

        print("Using OTSU Threshold")

        _, thresh = cv2.threshold(

            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU

        )

    else:

        print("Using Adaptive Threshold")

        thresh = cv2.adaptiveThreshold(

            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            15

        )

    return thresh


# =========================================================
# REMOVE THICK PAGE BORDERS
# =========================================================

def remove_borders(image):

    h, w = image.shape

    image[0:5, :] = 255
    image[h-5:h, :] = 255
    image[:, 0:5] = 255
    image[:, w-5:w] = 255

    return image


# =========================================================
# ADD OCR SAFE PADDING
# =========================================================

def add_padding(image, pad=20):

    padded = cv2.copyMakeBorder(

        image,
        pad,
        pad,
        pad,
        pad,
        cv2.BORDER_CONSTANT,
        value=255

    )

    return padded


# =========================================================
# MAIN PREPROCESSING
# =========================================================

def preprocess_image(image_path, output_folder):

    os.makedirs(

        output_folder,
        exist_ok=True

    )

    image = cv2.imread(image_path)

    if image is None:

        raise ValueError(

            f"Cannot read image → {image_path}"

        )

    print("\nStarting Industrial Preprocessing")

    h, w = image.shape[:2]

    print(f"Original Size → {w}x{h}")

    # =====================================================
    # UPSCALE SMALL IMAGES
    # =====================================================

    if w < 1200:

        image = cv2.resize(

            image,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC

        )

        print("Upscaled Small Image")

    # =====================================================
    # GRAYSCALE
    # =====================================================

    gray = cv2.cvtColor(

        image,
        cv2.COLOR_BGR2GRAY

    )

    # =====================================================
    # ANALYZE IMAGE
    # =====================================================

    metrics = analyze_image(gray)

    print(metrics)

    # =====================================================
    # DENOISE
    # =====================================================

    denoised = cv2.fastNlMeansDenoising(

        gray,
        None,
        10,
        7,
        21

    )

    # =====================================================
    # SHADOW REMOVAL
    # =====================================================

    shadow_free = remove_shadows(

        denoised

    )

    # =====================================================
    # NORMALIZE BRIGHTNESS
    # =====================================================

    normalized = normalize_brightness(

        shadow_free

    )

    # =====================================================
    # SAFE DESKEW
    # =====================================================

    deskewed = safe_deskew(

        normalized

    )

    # =====================================================
    # CLAHE CONTRAST ENHANCEMENT
    # =====================================================

    if metrics["contrast"] < 45:

        clahe = cv2.createCLAHE(

            clipLimit=2.0,
            tileGridSize=(8, 8)

        )

        enhanced = clahe.apply(

            deskewed

        )

    else:

        enhanced = deskewed

    # =====================================================
    # SHARPEN BLURRY IMAGE
    # =====================================================

    if metrics["blur"] < 100:

        gaussian = cv2.GaussianBlur(

            enhanced,
            (0, 0),
            3

        )

        enhanced = cv2.addWeighted(

            enhanced,
            1.5,
            gaussian,
            -0.5,
            0

        )

        print("Sharpening Applied")

    # =====================================================
    # THRESHOLD
    # =====================================================

    thresh = dynamic_threshold(

        enhanced,
        metrics["contrast"]

    )

    # =====================================================
    # MORPH CLEANUP
    # =====================================================

    cleaned = morphological_cleanup(

        thresh

    )

    # =====================================================
    # REMOVE BORDERS
    # =====================================================

    border_removed = remove_borders(

        cleaned

    )

    # =====================================================
    # OCR SAFE PADDING
    # =====================================================

    final_image = add_padding(

        border_removed

    )

    # =====================================================
    # SAVE OUTPUT
    # =====================================================

    output_path = os.path.join(

        output_folder,
        os.path.basename(image_path)

    )

    cv2.imwrite(

        output_path,
        final_image

    )

    print(f"Saved → {output_path}")

    return output_path






















# """
# image_preprocessing.py

# Generic, content-aware OCR preprocessing pipeline for Healthcare Intelligent
# Document Processing (IDP). Driven entirely by measurable image statistics —
# no document-type detection, no per-document-type branching logic.
# """

# import os
# import cv2
# import logging
# import numpy as np
# from dataclasses import dataclass, asdict
# from typing import Dict, Any, List, Tuple, Optional

# # ==============================================================================
# # CONFIGURABLE GLOBAL CONSTANTS (NO MAGIC NUMBERS)
# # ==============================================================================
# MIN_ACCEPTABLE_WIDTH: int = 1200
# MIN_ACCEPTABLE_HEIGHT: int = 1600

# BLUR_THRESHOLD: float = 110.0
# LOW_CONTRAST_THRESHOLD: float = 45.0
# HIGH_CONTRAST_THRESHOLD: float = 75.0
# LOW_BRIGHTNESS_THRESHOLD: float = 130.0
# HIGH_NOISE_THRESHOLD: float = 0.025
# UNEVEN_ILLUMINATION_THRESHOLD: float = 15.0
# MAX_DIGITAL_GRAPHICS_RATIO: float = 0.10
# MIN_SCAN_GRAPHICS_RATIO: float = 0.35
# MIN_SIGNIFICANT_ANGLE: float = 1.0
# MAX_STEERABLE_ANGLE: float = 15.0

# # Connected Component sizing constraints used to isolate alphanumeric text
# MIN_TEXT_AREA: int = 4
# MAX_TEXT_AREA_RATIO: float = 0.02
# MIN_TEXT_HEIGHT: int = 3
# MAX_TEXT_HEIGHT: int = 150
# MACRO_ELEMENT_RATIO: float = 0.015

# # Blob-cleanup shape constraints (relative to estimated character height)
# BLOB_MIN_ABS_AREA: int = 2          # absolute floor — true single-pixel speckle only
# BLOB_HEIGHT_RATIO_FLOOR: float = 0.12   # component shorter than this * char_height is suspect
# BLOB_MAX_ASPECT_RATIO: float = 6.0      # very elongated AND tiny => noise (hairline scan artifact)

# # Morphology kernel
# MORPHOLOGY_KERNEL_SIZE: Tuple[int, int] = (2, 2)

# logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
# logger = logging.getLogger("ProductionImagePreprocessor")


# @dataclass(frozen=True)
# class ImageMetricsReport:
#     blur: float
#     contrast: float
#     brightness: float
#     noise_density: float
#     background_uniformity: float
#     character_height: float
#     graphics_ratio: float
#     skew_angle: float
#     width: int
#     height: int


# @dataclass(frozen=True)
# class ProcessingRecipe:
#     apply_upscale: bool
#     apply_denoise: bool
#     apply_shadow_removal: bool
#     apply_clahe: bool
#     apply_sharpen: bool
#     apply_deskew: bool
#     apply_morphology: bool
#     threshold_mode: str        # "OTSU", "ADAPTIVE", "NONE"
#     adaptive_block_size: int
#     adaptive_constant_c: int


# # ==============================================================================
# # 1. METRIC FUNCTIONS  (each computes exactly one metric — no decisions here)
# # ==============================================================================

# def calculate_blur(gray: np.ndarray) -> float:
#     """Focus quality via variance of the Laplacian."""
#     return float(cv2.Laplacian(gray, cv2.CV_64F).var())


# def calculate_noise(total_labels: int, stats: np.ndarray, total_pixels: float) -> float:
#     """Density of near-singleton connected components (speckle noise proxy)."""
#     isolated = sum(1 for i in range(1, total_labels) if stats[i, cv2.CC_STAT_AREA] <= 2)
#     return float(isolated / total_pixels)


# def calculate_contrast(gray: np.ndarray) -> float:
#     return float(gray.std())


# def calculate_brightness(gray: np.ndarray) -> float:
#     return float(gray.mean())


# def _estimate_background_surface(gray: np.ndarray) -> np.ndarray:
#     """
#     Shared low-frequency background estimate used by both the background-
#     uniformity metric and shadow removal, so the algorithm is defined once.
#     """
#     dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
#     return cv2.medianBlur(dilated, 21)


# def calculate_background_uniformity(gray: np.ndarray, background: Optional[np.ndarray] = None) -> float:
#     """Spatial std-dev of (gray - estimated background); high = uneven illumination."""
#     background = background if background is not None else _estimate_background_surface(gray)
#     return float(np.std(cv2.absdiff(gray, background)))


# def calculate_character_scale(valid_heights: List[int]) -> float:
#     if not valid_heights:
#         return 16.0
#     return float(np.median(valid_heights))


# def calculate_graphics_coverage(large_graphical_areas: int, total_pixels: float) -> float:
#     return float(large_graphical_areas / total_pixels)


# def calculate_skew(thresh_noise: np.ndarray) -> float:
#     pts = cv2.findNonZero(thresh_noise)
#     if pts is None:
#         return 0.0
#     _, _, angle = cv2.minAreaRect(pts)
#     skew_angle = -(90 + angle) if angle < -45 else -angle
#     return float(round(skew_angle, 2))


# # ==============================================================================
# # 2. ANALYSIS CORE — single connected-components pass shared across metrics
# # ==============================================================================

# def analyze_image(gray: np.ndarray) -> Dict[str, Any]:
#     h, w = gray.shape[:2]
#     total_pixels = float(h * w)

#     _, thresh_noise = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
#     total_labels, _, stats, _ = cv2.connectedComponentsWithStats(thresh_noise, 8)

#     valid_heights: List[int] = []
#     large_graphical_areas: int = 0

#     for i in range(1, total_labels):
#         comp_h = stats[i, cv2.CC_STAT_HEIGHT]
#         area = stats[i, cv2.CC_STAT_AREA]
#         if MIN_TEXT_AREA <= area <= (total_pixels * MAX_TEXT_AREA_RATIO) and MIN_TEXT_HEIGHT <= comp_h <= MAX_TEXT_HEIGHT:
#             valid_heights.append(comp_h)
#         elif area > (total_pixels * MACRO_ELEMENT_RATIO):
#             large_graphical_areas += area

#     background_surface = _estimate_background_surface(gray)

#     report = ImageMetricsReport(
#         blur=calculate_blur(gray),
#         contrast=calculate_contrast(gray),
#         brightness=calculate_brightness(gray),
#         noise_density=calculate_noise(total_labels, stats, total_pixels),
#         background_uniformity=calculate_background_uniformity(gray, background_surface),
#         character_height=calculate_character_scale(valid_heights),
#         graphics_ratio=calculate_graphics_coverage(large_graphical_areas, total_pixels),
#         skew_angle=calculate_skew(thresh_noise),
#         width=w,
#         height=h,
#     )
#     return asdict(report)


# # ==============================================================================
# # 3. DECISION ENGINE — the ONLY place decisions are made
# # ==============================================================================

# def build_processing_recipe(metrics: Dict[str, Any]) -> Dict[str, Any]:
#     apply_upscale = (metrics["width"] < MIN_ACCEPTABLE_WIDTH) or (metrics["height"] < MIN_ACCEPTABLE_HEIGHT)
#     apply_denoise = metrics["noise_density"] > HIGH_NOISE_THRESHOLD
#     apply_shadow_removal = (metrics["background_uniformity"] > UNEVEN_ILLUMINATION_THRESHOLD) or (
#         metrics["brightness"] < LOW_BRIGHTNESS_THRESHOLD
#     )
#     apply_clahe = metrics["contrast"] < LOW_CONTRAST_THRESHOLD
#     apply_sharpen = (metrics["blur"] < BLUR_THRESHOLD) and (metrics["noise_density"] < HIGH_NOISE_THRESHOLD)
#     apply_deskew = MIN_SIGNIFICANT_ANGLE <= abs(metrics["skew_angle"]) <= MAX_STEERABLE_ANGLE

#     if (
#         metrics["contrast"] > HIGH_CONTRAST_THRESHOLD
#         and metrics["background_uniformity"] < UNEVEN_ILLUMINATION_THRESHOLD
#         and metrics["graphics_ratio"] < MAX_DIGITAL_GRAPHICS_RATIO
#     ):
#         threshold_mode = "OTSU"
#     elif (
#         metrics["contrast"] < LOW_CONTRAST_THRESHOLD
#         or metrics["background_uniformity"] > UNEVEN_ILLUMINATION_THRESHOLD
#         or metrics["graphics_ratio"] > MIN_SCAN_GRAPHICS_RATIO
#     ):
#         threshold_mode = "ADAPTIVE"
#     else:
#         threshold_mode = "NONE"

#     # Content-aware window: scales with detected character height, never with resolution.
#     calculated_block = int(metrics["character_height"] * 3)
#     if calculated_block % 2 == 0:
#         calculated_block += 1
#     adaptive_block_size = max(15, min(calculated_block, 251))
#     adaptive_constant_c = 12 if metrics["noise_density"] > HIGH_NOISE_THRESHOLD else 8

#     # Morphology only earns its cost when adaptive thresholding or high noise is present.
#     apply_morphology = (threshold_mode == "ADAPTIVE") or (metrics["noise_density"] > HIGH_NOISE_THRESHOLD)

#     recipe = ProcessingRecipe(
#         apply_upscale=apply_upscale,
#         apply_denoise=apply_denoise,
#         apply_shadow_removal=apply_shadow_removal,
#         apply_clahe=apply_clahe,
#         apply_sharpen=apply_sharpen,
#         apply_deskew=apply_deskew,
#         apply_morphology=apply_morphology,
#         threshold_mode=threshold_mode,
#         adaptive_block_size=adaptive_block_size,
#         adaptive_constant_c=adaptive_constant_c,
#     )
#     return asdict(recipe)


# # ==============================================================================
# # 4. PROCESSING FUNCTIONS — execute only, never decide
# # ==============================================================================

# def remove_shadows(gray: np.ndarray) -> np.ndarray:
#     """
#     Normalizes uneven illumination while preserving dynamic range: corrects the
#     background gradient via division rather than hard inversion/clipping, then
#     renormalizes back to the original intensity span.
#     """
#     background = _estimate_background_surface(gray)
#     background_safe = np.where(background == 0, 1, background).astype(np.float32)
#     corrected = (gray.astype(np.float32) / background_safe) * float(np.mean(background))
#     corrected = np.clip(corrected, 0, 255)
#     return cv2.normalize(corrected, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


# def safe_deskew(image: np.ndarray, angle: float) -> np.ndarray:
#     """Rotates the image to correct measured skew."""
#     h, w = image.shape[:2]
#     center = (w // 2, h // 2)
#     matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
#     return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


# def apply_clahe(gray: np.ndarray) -> np.ndarray:
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     return clahe.apply(gray)


# def sharpen(gray: np.ndarray) -> np.ndarray:
#     """Unsharp mask. Only invoked when recipe gates blur+noise jointly."""
#     gaussian = cv2.GaussianBlur(gray, (0, 0), 3)
#     return cv2.addWeighted(gray, 1.4, gaussian, -0.4, 0)


# def threshold(gray: np.ndarray, mode: str, block_size: int, c_val: int) -> np.ndarray:
#     if mode == "OTSU":
#         _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#         return binary
#     if mode == "ADAPTIVE":
#         return cv2.adaptiveThreshold(
#             gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_val
#         )
#     return gray.copy()


# def blob_cleanup(binary: np.ndarray, metrics: Dict[str, Any]) -> np.ndarray:
#     """
#     Removes genuine noise speckle while preserving small but legitimate glyphs
#     (periods, commas, colons, decimal points). Decision uses area, height,
#     width, and aspect ratio jointly — never area alone — so a small near-square
#     component (a period) survives even though its area is tiny.
#     """
#     if binary.ndim != 2 or binary.dtype != np.uint8:
#         return binary

#     char_h = max(metrics["character_height"], 1.0)
#     height_floor = max(2, char_h * BLOB_HEIGHT_RATIO_FLOOR)

#     inverted = cv2.bitwise_not(binary)
#     total_labels, labels, stats, _ = cv2.connectedComponentsWithStats(inverted, 8)

#     mask = np.zeros_like(inverted)
#     for i in range(1, total_labels):
#         area = stats[i, cv2.CC_STAT_AREA]
#         w = stats[i, cv2.CC_STAT_WIDTH]
#         h = stats[i, cv2.CC_STAT_HEIGHT]
#         aspect_ratio = max(w, h) / max(1, min(w, h))

#         # Hard floor: true sub-pixel speckle (almost certainly scan dust)
#         if area <= BLOB_MIN_ABS_AREA:
#             continue

#         # A component tall/wide enough relative to text height is kept regardless
#         # of small area — this is exactly what protects punctuation marks.
#         if h >= height_floor or w >= height_floor:
#             # Reject only if it's both extremely thin/elongated AND tiny in area —
#             # that combination indicates a hairline scan artifact, not a glyph.
#             if aspect_ratio > BLOB_MAX_ASPECT_RATIO and area <= BLOB_MIN_ABS_AREA * 4:
#                 continue
#             mask[labels == i] = 255

#     return cv2.bitwise_not(mask)


# def morphology(binary: np.ndarray) -> np.ndarray:
#     """Lightly closes broken strokes. Recipe-gated — not always executed."""
#     if binary.ndim != 2 or binary.dtype != np.uint8:
#         return binary
#     kernel = np.ones(MORPHOLOGY_KERNEL_SIZE, np.uint8)
#     opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
#     return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)


# def remove_borders(binary: np.ndarray) -> np.ndarray:
#     """Whites out scan-artifact margins. Margin width scales with resolution."""
#     if binary.ndim != 2:
#         return binary
#     h, w = binary.shape[:2]
#     margin = max(3, min(h, w) // 200)
#     processed = binary.copy()
#     processed[0:margin, :] = 255
#     processed[h - margin:h, :] = 255
#     processed[:, 0:margin] = 255
#     processed[:, w - margin:w] = 255
#     return processed


# def add_padding(binary: np.ndarray, pad: int = 20) -> np.ndarray:
#     return cv2.copyMakeBorder(binary, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)


# # ==============================================================================
# # 5. ORCHESTRATION PIPELINE
# # ==============================================================================

# def preprocess_image(image_path: str, output_folder: str) -> str:
#     """Runs the full content-aware preprocessing pipeline and writes the result."""
#     if not os.path.exists(image_path):
#         raise FileNotFoundError(f"Target document image not found: {image_path}")
#     os.makedirs(output_folder, exist_ok=True)

#     img = cv2.imread(image_path)
#     if img is None:
#         raise ValueError(f"Unable to decode image file: {image_path}")

#     h, w = img.shape[:2]
#     if w < MIN_ACCEPTABLE_WIDTH or h < MIN_ACCEPTABLE_HEIGHT:
#         img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#         logger.info(f"Upscaled low-resolution input from {w}x{h}")

#     canvas = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()

#     metrics = analyze_image(canvas)
#     recipe = build_processing_recipe(metrics)

#     logger.info(f"--- {os.path.basename(image_path)} ---")
#     logger.info(
#         "Metrics: Blur=%.1f Contrast=%.1f Brightness=%.1f Noise=%.4f "
#         "Uniformity=%.1f CharHeight=%.1f Graphics=%.4f Skew=%.2f°",
#         metrics["blur"], metrics["contrast"], metrics["brightness"], metrics["noise_density"],
#         metrics["background_uniformity"], metrics["character_height"], metrics["graphics_ratio"],
#         metrics["skew_angle"],
#     )
#     logger.info(
#         "Recipe: Upscale=%s Denoise=%s Shadow=%s CLAHE=%s Sharpen=%s Deskew=%s "
#         "Morph=%s Threshold=%s Block=%d C=%d",
#         recipe["apply_upscale"], recipe["apply_denoise"], recipe["apply_shadow_removal"],
#         recipe["apply_clahe"], recipe["apply_sharpen"], recipe["apply_deskew"],
#         recipe["apply_morphology"], recipe["threshold_mode"], recipe["adaptive_block_size"],
#         recipe["adaptive_constant_c"],
#     )

#     executed: List[str] = []

#     if recipe["apply_denoise"]:
#         canvas = cv2.bilateralFilter(canvas, d=9, sigmaColor=65, sigmaSpace=65)
#         executed.append("Denoise")

#     if recipe["apply_shadow_removal"]:
#         canvas = remove_shadows(canvas)
#         executed.append("ShadowRemoval")

#     if recipe["apply_deskew"]:
#         canvas = safe_deskew(canvas, metrics["skew_angle"])
#         executed.append("Deskew")

#     if recipe["apply_clahe"]:
#         canvas = apply_clahe(canvas)
#         executed.append("CLAHE")

#     if recipe["apply_sharpen"]:
#         canvas = sharpen(canvas)
#         executed.append("Sharpen")

#     canvas = threshold(canvas, recipe["threshold_mode"], recipe["adaptive_block_size"], recipe["adaptive_constant_c"])
#     executed.append(f"Threshold[{recipe['threshold_mode']}]")

#     canvas = blob_cleanup(canvas, metrics)
#     executed.append("BlobCleanup")

#     if recipe["apply_morphology"]:
#         canvas = morphology(canvas)
#         executed.append("Morphology")

#     canvas = remove_borders(canvas)
#     executed.append("BorderRemoval")

#     canvas = add_padding(canvas)
#     executed.append("Padding")

#     logger.info("Executed: " + " -> ".join(executed))

#     output_path = os.path.join(output_folder, f"processed_{os.path.basename(image_path)}")
#     cv2.imwrite(output_path, canvas)
#     return output_path
