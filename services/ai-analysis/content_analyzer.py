"""
Content Analyzer
================
Runs YOLO inference on video frames and maps detected objects to IAB content
categories, returning ad-targeting context for the SSAI engine.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import cv2
import numpy as np

from api.models import Detection
from yolo_scene_detector import YOLOSceneDetector

logger = logging.getLogger(__name__)

# ── IAB category mapping ──────────────────────────────────────────────────────
# Maps COCO class names to IAB Tech Lab content taxonomy categories.
# Extend this dictionary to improve targeting accuracy.
IAB_CATEGORY_MAP: Dict[str, List[str]] = {
    # Sports / outdoors
    "sports ball":      ["IAB17", "IAB17-18"],          # Sports > Ball sports
    "tennis racket":    ["IAB17", "IAB17-20"],           # Sports > Tennis
    "baseball bat":     ["IAB17", "IAB17-5"],            # Sports > Baseball
    "frisbee":          ["IAB17"],                       # Sports
    "snowboard":        ["IAB17", "IAB17-39"],           # Sports > Skiing/Snowboarding
    "skis":             ["IAB17", "IAB17-39"],
    "kite":             ["IAB17"],
    "surfboard":        ["IAB17", "IAB17-19"],
    "skateboard":       ["IAB17"],
    # Automotive
    "car":              ["IAB2"],                        # Automotive
    "truck":            ["IAB2"],
    "bus":              ["IAB2"],
    "motorcycle":       ["IAB2"],
    "bicycle":          ["IAB2"],
    # Food & Drink
    "banana":           ["IAB8"],                        # Food & Drink
    "apple":            ["IAB8"],
    "sandwich":         ["IAB8"],
    "pizza":            ["IAB8"],
    "hot dog":          ["IAB8"],
    "cake":             ["IAB8"],
    "wine glass":       ["IAB8"],
    "cup":              ["IAB8"],
    "fork":             ["IAB8"],
    "knife":            ["IAB8"],
    "spoon":            ["IAB8"],
    "bowl":             ["IAB8"],
    # Technology / Electronics
    "laptop":           ["IAB19"],                       # Technology & Computing
    "cell phone":       ["IAB19"],
    "keyboard":         ["IAB19"],
    "mouse":            ["IAB19"],
    "tv":               ["IAB19"],
    "monitor":          ["IAB19"],
    # Travel
    "airplane":         ["IAB20"],                       # Travel
    "boat":             ["IAB20"],
    "train":            ["IAB20"],
    # Pets & Animals
    "cat":              ["IAB16"],                       # Pets
    "dog":              ["IAB16"],
    # Home & Garden
    "couch":            ["IAB10"],                       # Home & Garden
    "bed":              ["IAB10"],
    "dining table":     ["IAB10"],
    "refrigerator":     ["IAB10"],
    "microwave":        ["IAB10"],
    "toaster":          ["IAB10"],
    "sink":             ["IAB10"],
    # Fitness
    "person":           ["IAB17-21"],                    # Sports > Walking
}


class ContentAnalyzer:
    """
    Analyses video frames with YOLO and produces IAB content categories
    and contextual ad-targeting metadata.
    """

    def __init__(self) -> None:
        self._detector = YOLOSceneDetector()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def analyze_frame(self, frame: np.ndarray) -> List[Detection]:
        """
        Run YOLO inference on a single BGR frame.

        Args:
            frame:  OpenCV BGR image as a NumPy array.

        Returns:
            List of Detection objects above the confidence threshold.
        """
        detections = self._detector.detect(frame)
        logger.debug("analyze_frame: %d detections", len(detections))
        return detections

    def classify_content(self, detections: List[Detection]) -> List[str]:
        """
        Map YOLO detections to deduplicated IAB content categories.

        Args:
            detections:  Output from analyze_frame().

        Returns:
            Sorted, deduplicated list of IAB category IDs.
        """
        categories: set[str] = set()
        for det in detections:
            iab = IAB_CATEGORY_MAP.get(det.class_name.lower())
            if iab:
                categories.update(iab)
        sorted_cats = sorted(categories)
        logger.debug("classify_content: categories=%s", sorted_cats)
        return sorted_cats

    def get_ad_context(
        self,
        frame: Optional[np.ndarray] = None,
        detections: Optional[List[Detection]] = None,
    ) -> Dict:
        """
        Return a context dictionary suitable for ad-server decision-making.

        Either a raw ``frame`` or pre-computed ``detections`` must be supplied.

        Returns:
            {
                "iab_categories": [...],
                "detected_objects": [...],
                "dominant_object": "person" | None,
                "object_count": 3,
                "confidence_avg": 0.82,
            }
        """
        if detections is None:
            if frame is None:
                raise ValueError("Either frame or detections must be provided")
            detections = self.analyze_frame(frame)

        iab_categories = self.classify_content(detections)

        object_names = [d.class_name for d in detections]
        dominant: Optional[str] = None
        if object_names:
            dominant = max(set(object_names), key=object_names.count)

        avg_conf = (
            sum(d.confidence for d in detections) / len(detections)
            if detections
            else 0.0
        )

        return {
            "iab_categories": iab_categories,
            "detected_objects": list({d.class_name for d in detections}),
            "dominant_object": dominant,
            "object_count": len(detections),
            "confidence_avg": round(avg_conf, 4),
        }
