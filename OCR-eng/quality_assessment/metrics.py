import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from .report import MetricResult

class DocumentMetricsEvaluator:
    """Mathematical extraction engine for isolated image properties."""

    @staticmethod
    def check_is_blank(gray: np.ndarray, standardized_regions: List[Dict[str, Any]]) -> bool:
        if standardized_regions:
            return False
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        if cv2.countNonZero(thresh) / (gray.shape[0] * gray.shape[1]) < 0.0010:
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours or max([cv2.contourArea(c) for c in contours], default=0) < 50:
                return True
        return False

    @staticmethod
    def extract_blur_variance(gray: np.ndarray) -> float:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def extract_edge_sharpness(gray: np.ndarray) -> float:
        """Measures high-frequency edge sharpness using Sobel filter magnitudes."""
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = cv2.magnitude(grad_x, grad_y)
        return float(np.mean(magnitude))

    @staticmethod
    def extract_contrast_std(gray: np.ndarray) -> float:
        return float(gray.std())

    @staticmethod
    def extract_histogram_range(gray: np.ndarray) -> float:
        """Calculates dynamic range spread by throwing out extreme white/black outliers."""
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = gray.shape[0] * gray.shape[1]
        
        # Identify the 1st and 99th pixel percentiles to ignore lighting noise
        cumulative = np.cumsum(hist)
        p1 = np.searchsorted(cumulative, total_pixels * 0.01)
        p99 = np.searchsorted(cumulative, total_pixels * 0.99)
        return float(p99 - p1)

    @staticmethod
    def extract_brightness_mean(gray: np.ndarray) -> float:
        return float(gray.mean())

    @staticmethod
    def extract_noise_variance(gray: np.ndarray) -> float:
        denoised = cv2.medianBlur(gray, 3)
        return float(np.mean(cv2.absdiff(gray, denoised)))

    @staticmethod
    def extract_resolution_dimensions(image: np.ndarray) -> tuple:
        return image.shape[0], image.shape[1]

    # @staticmethod
    # def extract_mathematical_coverage(gray: np.ndarray, standardized_regions: List[Dict[str, Any]]) -> float:
    #     """Computes true spatial union using pixel grid assignment matrix states to prevent overlap double-counting."""
    #     h_img, w_img = gray.shape[:2]
    #     total_area = h_img * w_img

    #     if standardized_regions:
    #         mask = np.zeros((h_img, w_img), dtype=np.uint8)
    #         for region in standardized_regions:
    #             # Direct interface unpack mapping standard [x1, y1, x2, y2]
    #             x1, y1, x2, y2 = [int(coord) for coord in region["bbox"]]
    #             # Apply fast geometric coordinate slicing boundaries
    #             mask[y1:y2, x1:x2] = 1
    #         return float(np.count_nonzero(mask) / total_area)

    #     # Fallback segmentation loop if YOLO drops out
    #     _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    #     return float(cv2.countNonZero(thresh) / total_area)


    @staticmethod
    def extract_mathematical_coverage(gray: np.ndarray, standardized_regions: List[Dict[str, Any]]) -> float:
        """Computes true spatial union using pixel grid assignment matrix states to prevent overlap double-counting."""
        h_img, w_img = gray.shape[:2]
        total_area = h_img * w_img

        if standardized_regions:
            mask = np.zeros((h_img, w_img), dtype=np.uint8)
            for region in standardized_regions:
                # INTERFACE SAFETIES: Dynamically look for 'box' or 'bbox' keys to prevent KeyErrors
                box_coordinates = region.get("box", region.get("bbox"))
                
                if not box_coordinates:
                    # Protection safeguard: skip if the region doesn't contain coordinates
                    continue
                    
                x1, y1, x2, y2 = [int(coord) for coord in box_coordinates]
                # Apply fast geometric coordinate slicing boundaries
                mask[y1:y2, x1:x2] = 1
            return float(np.count_nonzero(mask) / total_area)

        # Fallback segmentation loop if YOLO drops out
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return float(cv2.countNonZero(thresh) / total_area)


    @staticmethod
    def extract_skew_angle(gray: np.ndarray) -> float:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        pts = cv2.findNonZero(thresh)
        if pts is None:
            return 0.0
        _, _, angle = cv2.minAreaRect(pts)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        return float(round(angle, 2))

    @staticmethod
    def extract_text_density(gray: np.ndarray) -> int:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        total, _, stats, _ = cv2.connectedComponentsWithStats(thresh, 8)
        # Drop noise single-pixel components below 4 pixels
        return int(sum(1 for i in range(1, total) if stats[i, cv2.CC_STAT_AREA] >= 4))
