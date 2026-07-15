# import os
# import cv2
# from typing import Dict, Any, List, Optional
# from .report import ImageQualityReport, MetricResult, RoutingDecision
# from .metrics import DocumentMetricsEvaluator
# from .scoring import QualityScoringEngine

# class LayoutAwareQualityAnalyzer:
#     """
#     Orchestration wrapper implementing standard interfaces for the Image Quality Assessment Engine.
#     """

#     def __init__(self, profile_weights: Optional[Dict[str, float]] = None):
#         self.scorer = QualityScoringEngine(profile_weights)
#         self.MIN_OCR_THRESHOLD = 68.0

#     def analyze(self, image_path: str, layout_result: Optional[Dict[str, Any]] = None) -> ImageQualityReport:
#         image = cv2.imread(image_path)
#         if image is None:
#             raise FileNotFoundError(f"IQAE Orchestration Error: Cannot decode local file: {image_path}")

#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
#         # --- STANDARD INTERFACE MAPPING LAYER ---
#         # Decouples your YOLO framework tags from core logic variables
#         standardized_regions: List[Dict[str, Any]] = []
#         if layout_result:
#             # Map legacy 'cropped_regions', 'elements', or custom 'regions' arrays seamlessly here
#             standardized_regions = layout_result.get("regions", layout_result.get("cropped_regions", []))

#         # 1. Fast-Pass Blank Verification
#         if DocumentMetricsEvaluator.check_is_blank(gray, standardized_regions):
#             blank_metric = MetricResult(0.0, 100.0)
#             return ImageQualityReport(
#                 is_blank=True, blur=blank_metric, edge_sharpness=blank_metric, contrast=blank_metric,
#                 histogram_range=blank_metric, brightness=MetricResult(float(gray.mean()), 100.0),
#                 noise=blank_metric, resolution_score=100.0, document_coverage=blank_metric,
#                 text_density=blank_metric, skew_angle=blank_metric, overall_score=100.0,
#                 recommendation=RoutingDecision.BLANK
#             )

#         # 2. Extract Raw Metrics Variables
#         raw_blur = DocumentMetricsEvaluator.extract_blur_variance(gray)
#         raw_edge = DocumentMetricsEvaluator.extract_edge_sharpness(gray)
#         raw_contrast = DocumentMetricsEvaluator.extract_contrast_std(gray)
#         raw_hist = DocumentMetricsEvaluator.extract_histogram_range(gray)
#         raw_bright = DocumentMetricsEvaluator.extract_brightness_mean(gray)
#         raw_noise = DocumentMetricsEvaluator.extract_noise_variance(gray)
#         h, w = DocumentMetricsEvaluator.extract_resolution_dimensions(image)
#         raw_coverage = DocumentMetricsEvaluator.extract_mathematical_coverage(gray, standardized_regions)
#         raw_density = DocumentMetricsEvaluator.extract_text_density(gray)
#         raw_skew = DocumentMetricsEvaluator.extract_skew_angle(gray)

#         # 3. Compile Normalized MetricResult Structures
#         blur_res = MetricResult(raw_blur, self.scorer.score_blur(raw_blur))
#         edge_res = MetricResult(raw_edge, self.scorer.score_edge_sharpness(raw_edge))
#         contrast_res = MetricResult(raw_contrast, self.scorer.score_contrast(raw_contrast))
#         hist_res = MetricResult(raw_hist, self.scorer.score_histogram_range(raw_hist))
#         bright_res = MetricResult(raw_bright, self.scorer.score_brightness(raw_bright))
#         noise_res = MetricResult(raw_noise, self.scorer.score_noise(raw_noise))
#         res_score = self.scorer.score_resolution(h, w)
#         coverage_res = MetricResult(raw_coverage, self.scorer.score_coverage(raw_coverage, bool(standardized_regions)))
#         density_res = MetricResult(raw_density, self.scorer.score_density(raw_density, h, w))
#         skew_res = MetricResult(raw_skew, self.scorer.score_skew(raw_skew))

#         # # 4. Process Unified Weights Ledger
#         # w_matrix = self.scorer.weights
#         # overall_score = (
#         #     blur_res.normalized_score * w_matrix["blur"] +
#         #     edge_res.normalized_score * w_matrix["edge_sharpness"] +
#         #     contrast_res.normalized_score * w_matrix["contrast"] +
#         #     hist_res.normalized_score * w_matrix["histogram_range"] +
#         #     bright_res.normalized_score * w_matrix["brightness"] +
#         #     noise_res.normalized_score * w_matrix["noise"] +
#         #     res_score * w_matrix["resolution"] +
#         #     coverage_res.normalized_score * w_matrix["coverage"] +
#         #     density_res.normalized_score * w_matrix["density"] +
#         #     skew_res.normalized_score * w_matrix["skew"]
#         # )

#         # decision = RoutingDecision.OCR if overall_score >= self.MIN_OCR_THRESHOLD else RoutingDecision.VISION

#         # return ImageQualityReport(
#         #     is_blank=False, blur=blur_res, edge_sharpness=edge_res, contrast=contrast_res,
#         #     histogram_range=hist_res, brightness=bright_res, noise=noise_res, resolution_score=res_score,
#         #     document_coverage=coverage_res, text_density=density_res, skew_angle=skew_res,
#         #     overall_score=round(max(0.0, overall_score), 2), recommendation=decision
#         # )

#         # 4. Process Unified Weights Ledger
#         w_matrix = self.scorer.weights
#         overall_score = (
#             blur_res.normalized_score * w_matrix["blur"] +
#             edge_res.normalized_score * w_matrix["edge_sharpness"] +
#             contrast_res.normalized_score * w_matrix["contrast"] +
#             hist_res.normalized_score * w_matrix["histogram_range"] +
#             bright_res.normalized_score * w_matrix["brightness"] +
#             noise_res.normalized_score * w_matrix["noise"] +
#             res_score * w_matrix["resolution"] +
#             coverage_res.normalized_score * w_matrix["coverage"] +
#             density_res.normalized_score * w_matrix["density"] +
#             skew_res.normalized_score * w_matrix["skew"]
#         )

#         # --- THE PRODUCTION POINT-BY-POINT OVERRIDE GATE ---
#         # Isolate critical risk vectors for traditional OCR engines
#         is_too_noisy = noise_res.normalized_score < 50.0
#         is_blurry = blur_res.normalized_score < 60.0
#         is_soft_edges = edge_res.normalized_score < 60.0

#         if is_too_noisy or is_blurry or is_soft_edges:
#             # FORCE VISION LLM ROUTE: Point failures override the weighted aggregate average
#             decision = RoutingDecision.VISION
#         else:
#             # Standard Route: Passes only if all key vectors are healthy
#             decision = RoutingDecision.OCR if overall_score >= self.MIN_OCR_THRESHOLD else RoutingDecision.VISION

#         return ImageQualityReport(
#             is_blank=False, blur=blur_res, edge_sharpness=edge_res, contrast=contrast_res,
#             histogram_range=hist_res, brightness=bright_res, noise=noise_res, resolution_score=res_score,
#             document_coverage=coverage_res, text_density=density_res, skew_angle=skew_res,
#             overall_score=round(max(0.0, overall_score), 2), recommendation=decision
#         )

# # ==========================================================
# # SYSTEM VERIFICATION AND RUNTIME EXAMPLE
# # ==========================================================
# if __name__ == "__main__":
#     import json
    
#     # Standard Interface Example: Properly closed mock bounding box coordinate parameters
#     mock_yolo_result = {
#         "status": "success",
#         "regions": [
#             {
#                 "label": "header_logo",
#                 "bbox": [20, 30, 180, 120],
#                 "confidence": 0.98
#             },
#             {
#                 "label": "billing_table",
#                 "bbox": [100, 250, 1800, 2600],
#                 "confidence": 0.95
#             }
#         ]
#     }

#     # Initialize Engine Components
#     analyzer = LayoutAwareQualityAnalyzer()
    
#     # Optional test mock target image parameters
#     image_path_target = os.path.join("Result", "images", "page_01.jpg")
#     print("IQAE Engine Script syntax checks clean. Ready for modular deployment.")
    
#     # To run validation manually, ensure page_01.jpg exists and uncomment rows below:
#     # try:
#     #     report = analyzer.analyze(image_path=image_path_target, layout_result=mock_yolo_result)
#     #     print(f"Recommendation Decision Enum: {report.recommendation}")
#     #     print(json.dumps(report.to_dict(), indent=4))
#     # except FileNotFoundError as err:
#     #     print(f"Syntax runs cleanly, test skipped: {err}")








import os
import cv2
import base64
import logging
import openai  # Used to connect natively to local Ollama or vLLM vision endpoints
from typing import Dict, Any, List, Optional
from .report import ImageQualityReport, MetricResult, RoutingDecision
from .metrics import DocumentMetricsEvaluator
from .scoring import QualityScoringEngine

logger = logging.getLogger("Tamil_Software_IDP_Router")

# ==========================================================================
# LOCAL HARDWARE ORCHESTRATION (NO PAID API KEY REQUIRED)
# ==========================================================================
local_llm_client = openai.AsyncOpenAI(
    base_url="http://localhost:11434/v1",  # Standard local Ollama port on your PC/Server
    api_key="ollama_local_in_house",     # Functional placeholder string for local endpoints
    timeout=300
)

class LayoutAwareQualityAnalyzer:
    """
    Orchestration wrapper implementing standard interfaces for the Image Quality Assessment Engine.
    Handles both document quality point check analysis and local pixel-level visual text extraction.
    """

    def __init__(self, profile_weights: Optional[Dict[str, float]] = None):
        self.scorer = QualityScoringEngine(profile_weights)
        self.MIN_OCR_THRESHOLD = 68.0

    @staticmethod
    def _convert_image_to_base64(image_path: str) -> str:

        image = cv2.imread(image_path)

        if image is None:
            raise FileNotFoundError(image_path)

        h, w = image.shape[:2]

        max_side = 1280

        scale = min(max_side / w, max_side / h)

        if scale < 1:
            image = cv2.resize(
                image,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_AREA
            )

        _, buffer = cv2.imencode(
            ".jpg",
            image,
            [cv2.IMWRITE_JPEG_QUALITY, 80]
        )

        return base64.b64encode(buffer).decode("utf-8")

    # ==========================================================================
    # GENERIC LOCAL RAW TEXT VISUAL TRANSCRIPTION LAYER (QWEN VISION)
    # ==========================================================================
    async def extract_via_vision_llm(self, image_path: str, target_prompt: str) -> str:
        """
        Connects to your local QWNEN model to read text directly 
        from pixels and return a clean, unformatted raw transcript string.
        """
        try:

            print("="*80)
            print("VISION LLM")
            print("Image Path:", image_path)
            print("Exists:", os.path.exists(image_path))

            image = cv2.imread(image_path)

            if image is None:
                print("FAILED TO LOAD IMAGE")
            else:
                print("Shape:", image.shape)

            print("="*80)

            base64_image = self._convert_image_to_base64(image_path)
            
            response = await local_llm_client.chat.completions.create(
                model="qwen2.5vl:7b",  # Instantiated local weights on your machine hardware
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": target_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                temperature=0.0,
                response_format=None,  # Forces QWEN to output a raw, unformatted string instead of JSON
                # --- ADD THIS ENTERPRISE HARDWARE GUARDRAIL ---
                extra_body={
                    "options": {
                        # "num_ctx": 8192,     # Caps the local token window to shield your GPU VRAM
                        # "num_predict": 1024   # Limits text response lengths to prevent model looping

                        "num_ctx": 2048,
                        "num_predict": 512
                    }
                }
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"In-house local Qwen Vision request dropped out: {str(e)}")
            return f"[ERROR] Local Vision LLM processing failed: {str(e)}"

    # ==========================================================================
    # IMAGE METRIC ANALYSIS PIPELINE
    # ==========================================================================
    def analyze(self, image_path: str, layout_result: Optional[Dict[str, Any]] = None) -> ImageQualityReport:
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"IQAE Orchestration Error: Cannot decode local file: {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # --- STANDARD INTERFACE MAPPING LAYER ---
        standardized_regions: List[Dict[str, Any]] = []
        if layout_result:
            standardized_regions = layout_result.get("regions", layout_result.get("cropped_regions", []))

        # 1. Fast-Pass Blank Verification
        if DocumentMetricsEvaluator.check_is_blank(gray, standardized_regions):
            blank_metric = MetricResult(0.0, 100.0)
            return ImageQualityReport(
                is_blank=True, blur=blank_metric, edge_sharpness=blank_metric, contrast=blank_metric,
                histogram_range=blank_metric, brightness=MetricResult(float(gray.mean()), 100.0),
                noise=blank_metric, resolution_score=100.0, document_coverage=blank_metric,
                text_density=blank_metric, skew_angle=blank_metric, overall_score=100.0,
                recommendation=RoutingDecision.BLANK
            )

        # 2. Extract Raw Metrics Variables
        raw_blur = DocumentMetricsEvaluator.extract_blur_variance(gray)
        raw_edge = DocumentMetricsEvaluator.extract_edge_sharpness(gray)
        raw_contrast = DocumentMetricsEvaluator.extract_contrast_std(gray)
        raw_hist = DocumentMetricsEvaluator.extract_histogram_range(gray)
        raw_bright = DocumentMetricsEvaluator.extract_brightness_mean(gray)
        raw_noise = DocumentMetricsEvaluator.extract_noise_variance(gray)
        h, w = DocumentMetricsEvaluator.extract_resolution_dimensions(image)
        raw_coverage = DocumentMetricsEvaluator.extract_mathematical_coverage(gray, standardized_regions)
        raw_density = DocumentMetricsEvaluator.extract_text_density(gray)
        raw_skew = DocumentMetricsEvaluator.extract_skew_angle(gray)

        # 3. Compile Normalized MetricResult Structures
        blur_res = MetricResult(raw_blur, self.scorer.score_blur(raw_blur))
        edge_res = MetricResult(raw_edge, self.scorer.score_edge_sharpness(raw_edge))
        contrast_res = MetricResult(raw_contrast, self.scorer.score_contrast(raw_contrast))
        hist_res = MetricResult(raw_hist, self.scorer.score_histogram_range(raw_hist))
        bright_res = MetricResult(raw_bright, self.scorer.score_brightness(raw_bright))
        noise_res = MetricResult(raw_noise, self.scorer.score_noise(raw_noise))
        res_score = self.scorer.score_resolution(h, w)
        coverage_res = MetricResult(raw_coverage, self.scorer.score_coverage(raw_coverage, bool(standardized_regions)))
        density_res = MetricResult(raw_density, self.scorer.score_density(raw_density, h, w))
        skew_res = MetricResult(raw_skew, self.scorer.score_skew(raw_skew))

        # 4. Process Unified Weights Ledger
        w_matrix = self.scorer.weights
        overall_score = (
            blur_res.normalized_score * w_matrix["blur"] +
            edge_res.normalized_score * w_matrix["edge_sharpness"] +
            contrast_res.normalized_score * w_matrix["contrast"] +
            hist_res.normalized_score * w_matrix["histogram_range"] +
            bright_res.normalized_score * w_matrix["brightness"] +
            noise_res.normalized_score * w_matrix["noise"] +
            res_score * w_matrix["resolution"] +
            coverage_res.normalized_score * w_matrix["coverage"] +
            density_res.normalized_score * w_matrix["density"] +
            skew_res.normalized_score * w_matrix["skew"]
        )

        # --- THE PRODUCTION POINT-BY-POINT OVERRIDE GATE ---
        is_too_noisy = noise_res.normalized_score < 50.0
        is_blurry = blur_res.normalized_score < 60.0
        is_soft_edges = edge_res.normalized_score < 60.0

        if is_too_noisy or is_blurry or is_soft_edges:
            # FORCE VISION LLM ROUTE: Point failures override the weighted aggregate average
            decision = RoutingDecision.VISION
        else:
            # Standard Route: Passes only if all key vectors are healthy
            decision = RoutingDecision.OCR if overall_score >= self.MIN_OCR_THRESHOLD else RoutingDecision.VISION

        return ImageQualityReport(
            is_blank=False, blur=blur_res, edge_sharpness=edge_res, contrast=contrast_res,
            histogram_range=hist_res, brightness=bright_res, noise=noise_res, resolution_score=res_score,
            document_coverage=coverage_res, text_density=density_res, skew_angle=skew_res,
            overall_score=round(max(0.0, overall_score), 2), recommendation=decision
        )

# ==========================================================
# SYSTEM VERIFICATION AND RUNTIME EXAMPLE
# ==========================================================
# if __name__ == "__main__":
#     import json
    
#     mock_yolo_result = {
#         "status": "success",
#         "regions": [
#             {
#                 "label": "header_logo",
#                 "bbox":,
#                 "confidence": 0.98
#             },
#             {
#                 "label": "billing_table",
#                 "bbox":,
#                 "confidence": 0.95
#             }
#         ]
#     }

#     analyzer = LayoutAwareQualityAnalyzer()
#     print("IQAE Engine Script syntax checks clean. Ready for modular deployment.")




# ==========================================================
# SYSTEM VERIFICATION AND RUNTIME EXAMPLE
# ==========================================================
if __name__ == "__main__":

    import json

    mock_yolo_result = {
        "status": "success",
        "regions": [
            {
                "label": "header_logo",
                "bbox": [20, 20, 220, 120],
                "confidence": 0.98
            },
            {
                "label": "billing_table",
                "bbox": [100, 250, 1800, 2600],
                "confidence": 0.95
            }
        ]
    }

    analyzer = LayoutAwareQualityAnalyzer()

    print("IQAE Engine Script syntax checks clean. Ready for modular deployment.")