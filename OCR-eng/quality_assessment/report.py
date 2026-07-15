from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any

class RoutingDecision(Enum):
    OCR = "OCR"
    VISION = "VISION_LLM"
    BLANK = "BLANK_PAGE"

@dataclass(frozen=True)
class MetricResult:
    raw_value: float
    normalized_score: float

@dataclass(frozen=True)
class ImageQualityReport:
    is_blank: bool
    blur: MetricResult
    edge_sharpness: MetricResult
    contrast: MetricResult
    histogram_range: MetricResult
    brightness: MetricResult
    noise: MetricResult
    resolution_score: float
    document_coverage: MetricResult
    text_density: MetricResult
    skew_angle: MetricResult
    overall_score: float
    recommendation: RoutingDecision

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Convert Enum to string values for direct downstream JSON serialization compatibility
        result["recommendation"] = self.recommendation.value
        return result
