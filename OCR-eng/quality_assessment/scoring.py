from typing import Dict, Any, List, Optional
from .report import MetricResult

class QualityScoringEngine:
    """Normalizes raw physical metrics into stable score spaces from 0 to 100."""

    def __init__(self, profile_weights: Optional[Dict[str, float]] = None):
        self.weights = profile_weights or {
            "blur": 0.20,
            "edge_sharpness": 0.15,
            "contrast": 0.10,
            "histogram_range": 0.10,
            "brightness": 0.05,
            "noise": 0.15,
            "resolution": 0.05,
            "coverage": 0.10,
            "density": 0.05,
            "skew": 0.05
        }
        # Strict Enterprise Rule Verification Guardrail
        if abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError(f"IQAE Configuration Fatal Error: Weights must sum to exactly 1.0. Current: {sum(self.weights.values())}")

    def score_blur(self, val: float) -> float:
        if val >= 250: return 100.0
        if val >= 150: return 85.0
        if val >= 80:  return 65.0
        return 30.0 if val >= 40 else 10.0

    def score_edge_sharpness(self, val: float) -> float:
        """Maps Sobel pixel magnitudes to clean text edge readability curves."""
        if val >= 12.0: return 100.0
        if val >= 8.0:  return 85.0
        if val >= 4.0:  return 60.0
        return 35.0 if val >= 2.0 else 10.0

    def score_contrast(self, val: float) -> float:
        if val >= 50.0: return 100.0
        if val >= 35.0: return 85.0
        return 60.0 if val >= 20.0 else 20.0

    def score_histogram_range(self, val: float) -> float:
        """Scores dynamic range spreads to isolate gray, washed-out images."""
        if val >= 180.0: return 100.0
        if val >= 120.0: return 80.0
        return 50.0 if val >= 60.0 else 15.0

    def score_brightness(self, val: float) -> float:
        if 85.0 <= val <= 225.0: return 100.0
        return max(0.0, 100.0 - (abs(val - 155.0) * 0.8))

    def score_noise(self, val: float) -> float:
        """
        Production Hardening: Severely drops the score if background 
        dot noise or photocopy artifacts exceed baseline parameters.
        """
        if val <= 1.2: return 100.0
        if val <= 2.5: return 85.0
        if val <= 4.5: return 55.0
        # Steep enterprise dropoff curve to capture heavy dot distortion
        if val <= 7.0: return 25.0
        return 0.0
    
    def score_resolution(self, h: int, w: int) -> float:
        if w >= 1200 and h >= 1600: return 100.0
        return round(min(w / 1200.0, h / 1600.0) * 100, 2)

    def score_coverage(self, ratio: float, has_regions: bool) -> float:
        if has_regions:
            return 100.0 if ratio >= 0.35 else (ratio / 0.35) * 100
        return 100.0 if 0.04 <= ratio <= 0.45 else 45.0

    def score_density(self, components: int, h: int, w: int) -> float:
        page_area_inches = (h * w) / (300 * 300)
        density_ratio = components / max(1.0, page_area_inches)
        if 40 <= density_ratio <= 1600: return 100.0
        return 70.0 if density_ratio > 1600 else 40.0

    def score_skew(self, angle: float) -> float:
        abs_angle = abs(angle)
        if abs_angle <= 2.0:  return 100.0
        if abs_angle <= 6.0:  return 85.0
        if abs_angle <= 12.0: return 60.0
        return 30.0 if abs_angle <= 20.0 else 5.0
