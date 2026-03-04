"""
YOLO Scene Detector
===================
Uses YOLOv8 to detect objects frame-by-frame and identify scene changes
based on the cosine similarity of consecutive detection histograms.

Scene changes are surfaced as SCTE-35 ad-insertion opportunities.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, List, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from api.models import Detection, SceneChange

logger = logging.getLogger(__name__)

# Default model path — can be overridden via YOLO_MODEL env var
MODEL_PATH = os.environ.get("YOLO_MODEL", "yolov8n.pt")
MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/app/models")

# Scene-change detection thresholds
SCENE_CHANGE_THRESHOLD = float(os.environ.get("SCENE_CHANGE_THRESHOLD", "0.35"))
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.40"))


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity between two 1-D vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _detections_to_histogram(detections: List[Detection], num_classes: int = 80) -> np.ndarray:
    """
    Convert a list of detections to a class-presence histogram.
    Each bucket corresponds to a COCO class index, weighted by confidence.
    """
    hist = np.zeros(num_classes, dtype=np.float32)
    for det in detections:
        idx = det.class_id
        if 0 <= idx < num_classes:
            hist[idx] += det.confidence
    return hist


class YOLOSceneDetector:
    """
    Wraps a YOLOv8 model to perform frame-by-frame object detection and
    scene-change detection based on object-composition cosine similarity.
    """

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        full_path = Path(MODEL_CACHE_DIR) / Path(model_path).name
        # Use cached model if available, otherwise let Ultralytics download it
        effective_path = str(full_path) if full_path.exists() else model_path
        logger.info("Loading YOLO model from %s", effective_path)
        self.model = YOLO(effective_path)
        self._prev_histogram: Optional[np.ndarray] = None
        logger.info("YOLO model loaded successfully")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run inference on a single BGR frame, return Detection objects."""
        results = self.model(frame, verbose=False)[0]
        detections: List[Detection] = []
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < MIN_CONFIDENCE:
                continue
            cls_id = int(box.cls[0])
            cls_name = self.model.names.get(cls_id, str(cls_id))
            x1, y1, x2, y2 = map(float, box.xyxy[0])
            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                )
            )
        return detections

    def is_scene_change(self, current: List[Detection]) -> tuple[bool, float]:
        """
        Compare current detections to the previous frame's histogram.

        Returns:
            (is_change, dissimilarity_score) where dissimilarity in [0, 1].
        """
        hist = _detections_to_histogram(current)
        if self._prev_histogram is None:
            self._prev_histogram = hist
            return False, 0.0

        similarity = _cosine_similarity(hist, self._prev_histogram)
        dissimilarity = 1.0 - similarity
        self._prev_histogram = hist
        return dissimilarity >= SCENE_CHANGE_THRESHOLD, dissimilarity

    def batch_process_video(
        self,
        video_path: str,
        sample_every_n: int = 15,
    ) -> List[SceneChange]:
        """
        Process a VOD file and return all detected scene changes.

        Args:
            video_path:      Path to the local video file.
            sample_every_n:  Analyse every N-th frame (default 15 ≈ 0.5 fps at 30 fps).

        Returns:
            Ordered list of SceneChange events.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        scene_changes: List[SceneChange] = []
        frame_idx = 0
        prev_detections: List[Detection] = []

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_every_n == 0:
                    timestamp = frame_idx / fps
                    current_detections = self.detect(frame)
                    is_change, score = self.is_scene_change(current_detections)

                    if is_change:
                        scene_changes.append(
                            SceneChange(
                                timestamp=timestamp,
                                confidence=score,
                                objects_before=[d.class_name for d in prev_detections],
                                objects_after=[d.class_name for d in current_detections],
                            )
                        )
                        logger.debug(
                            "Scene change at %.2fs (score=%.3f)", timestamp, score
                        )

                    prev_detections = current_detections

                frame_idx += 1
        finally:
            cap.release()

        logger.info(
            "batch_process_video: %d scene changes in %d frames",
            len(scene_changes),
            frame_idx,
        )
        return scene_changes

    async def detect_scene_changes_from_stream(
        self,
        stream_url: str,
        sample_every_n: int = 15,
    ) -> AsyncGenerator[SceneChange, None]:
        """
        Async generator that connects to an RTMP/HLS stream URL and yields
        SceneChange events in real time.

        Args:
            stream_url:      RTMP or HLS URL.
            sample_every_n:  Analyse every N-th frame.
        """
        logger.info("Connecting to stream: %s", stream_url)
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            raise ConnectionError(f"Cannot open stream: {stream_url}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        prev_detections: List[Detection] = []

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    # Give the stream a moment to recover
                    await asyncio.sleep(0.1)
                    continue

                if frame_idx % sample_every_n == 0:
                    timestamp = frame_idx / fps
                    # Offload blocking inference to a thread pool
                    current_detections = await asyncio.get_running_loop().run_in_executor(
                        None, self.detect, frame
                    )
                    is_change, score = self.is_scene_change(current_detections)

                    if is_change:
                        change = SceneChange(
                            timestamp=timestamp,
                            confidence=score,
                            objects_before=[d.class_name for d in prev_detections],
                            objects_after=[d.class_name for d in current_detections],
                        )
                        logger.info(
                            "Scene change at %.2fs (score=%.3f)", timestamp, score
                        )
                        yield change

                    prev_detections = current_detections

                frame_idx += 1
                # Yield control to event loop between frames
                await asyncio.sleep(0)
        finally:
            cap.release()
            logger.info("Stream processing stopped after %d frames", frame_idx)
