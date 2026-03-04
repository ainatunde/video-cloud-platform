"""
AI Analysis Service — FastAPI application
==========================================
Exposes REST and WebSocket endpoints for frame/video analysis using YOLOv8.
"""
from __future__ import annotations

import base64
import io
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from api.models import AnalysisRequest, AnalysisResponse, Detection, SceneChange
from content_analyzer import ContentAnalyzer
from yolo_scene_detector import YOLOSceneDetector

logger = logging.getLogger(__name__)

# Restrict video file access to this directory (set to "" to disable)
VIDEO_BASE_DIR = os.environ.get("VIDEO_BASE_DIR", "/data")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

# ── Application-level singletons ─────────────────────────────────────────────
_analyzer: ContentAnalyzer | None = None
_detector: YOLOSceneDetector | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load models once at startup; release resources on shutdown."""
    global _analyzer, _detector
    logger.info("Loading AI models…")
    _analyzer = ContentAnalyzer()
    _detector = _analyzer._detector
    logger.info("Models ready.")
    yield
    logger.info("Shutting down AI analysis service.")


app = FastAPI(
    title="AI Analysis Service",
    description="YOLOv8 scene detection and content classification",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base64_to_frame(b64: str) -> np.ndarray:
    """Decode a base64 image string to an OpenCV BGR array."""
    try:
        raw = base64.b64decode(b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 data: {exc}") from exc

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _validate_video_path(path: str) -> None:
    """Reject paths that escape VIDEO_BASE_DIR to prevent path traversal."""
    if not VIDEO_BASE_DIR:
        return
    try:
        resolved = Path(path).resolve()
        base = Path(VIDEO_BASE_DIR).resolve()
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"video_path must be inside {VIDEO_BASE_DIR}",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid video_path: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok", "model_loaded": _detector is not None}


@app.post("/analyze/frame", response_model=AnalysisResponse, tags=["analysis"])
async def analyze_frame(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyse a single video frame supplied as base64-encoded image data.

    Returns YOLO detections and IAB content categories.
    """
    if _analyzer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    if not request.image_base64:
        raise HTTPException(status_code=422, detail="image_base64 is required")

    t0 = time.perf_counter()
    frame = _base64_to_frame(request.image_base64)
    detections: list[Detection] = _analyzer.analyze_frame(frame)
    categories = _analyzer.classify_content(detections)
    elapsed = (time.perf_counter() - t0) * 1000

    return AnalysisResponse(
        detections=detections,
        content_categories=categories,
        processing_time_ms=round(elapsed, 2),
    )


@app.post("/analyze/video", response_model=AnalysisResponse, tags=["analysis"])
async def analyze_video(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyse a VOD file at the given local path.

    Returns all detected scene changes and the overall content categories.
    """
    if _detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    if not request.video_path:
        raise HTTPException(status_code=422, detail="video_path is required")
    _validate_video_path(request.video_path)

    t0 = time.perf_counter()
    try:
        scene_changes: list[SceneChange] = _detector.batch_process_video(
            request.video_path, sample_every_n=request.sample_every_n
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    elapsed = (time.perf_counter() - t0) * 1000

    # Derive overall categories from objects seen across all changes
    all_objects = set()
    for sc in scene_changes:
        all_objects.update(sc.objects_after)

    # Re-use classify_content by building synthetic detections
    synthetic = [
        Detection(class_id=0, class_name=name, confidence=1.0, bbox=[0, 0, 1, 1])
        for name in all_objects
    ]
    categories = _analyzer.classify_content(synthetic)

    return AnalysisResponse(
        scene_changes=scene_changes,
        content_categories=categories,
        processing_time_ms=round(elapsed, 2),
    )


@app.websocket("/ws/stream")
async def ws_stream_analysis(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time stream analysis.

    The client sends the stream URL as the first text message.
    The server streams back JSON-encoded SceneChange events as they occur.

    Message format (client → server):
        {"stream_url": "rtmp://...", "sample_every_n": 15}

    Message format (server → client):
        SceneChange JSON object
    """
    await websocket.accept()
    try:
        config = await websocket.receive_json()
        stream_url = config.get("stream_url")
        sample_n = int(config.get("sample_every_n", 15))

        if not stream_url:
            await websocket.send_json({"error": "stream_url is required"})
            await websocket.close(code=1003)
            return

        logger.info("WS /ws/stream: starting analysis of %s", stream_url)
        async for change in _detector.detect_scene_changes_from_stream(
            stream_url, sample_every_n=sample_n
        ):
            await websocket.send_text(change.model_dump_json())

    except WebSocketDisconnect:
        logger.info("WS client disconnected from /ws/stream")
    except Exception as exc:
        logger.exception("WS /ws/stream error: %s", exc)
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
        await websocket.close(code=1011)
