"""
Pydantic models for the AI analysis service API.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """A single object detection from the YOLO model."""
    class_id: int = Field(..., description="COCO class index")
    class_name: str = Field(..., description="Human-readable class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bbox: List[float] = Field(
        ..., min_length=4, max_length=4,
        description="Bounding box [x1, y1, x2, y2] in pixel coordinates"
    )


class SceneChange(BaseModel):
    """A detected scene change, used as an ad-insertion opportunity."""
    timestamp: float = Field(..., description="Stream timestamp in seconds")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Dissimilarity score")
    objects_before: List[str] = Field(default_factory=list, description="Objects in the previous scene")
    objects_after: List[str] = Field(default_factory=list, description="Objects in the new scene")


class AnalysisRequest(BaseModel):
    """Request body for /analyze/frame and /analyze/video."""
    image_base64: Optional[str] = Field(
        None, description="Base64-encoded JPEG/PNG frame for single-frame analysis"
    )
    video_path: Optional[str] = Field(
        None, description="Absolute path to a local video file for VOD analysis"
    )
    stream_url: Optional[str] = Field(
        None, description="RTMP or HLS URL for live stream analysis"
    )
    sample_every_n: int = Field(
        15, ge=1, description="Analyse every N-th frame (VOD / live)"
    )


class AnalysisResponse(BaseModel):
    """Response body for analysis endpoints."""
    scene_changes: List[SceneChange] = Field(default_factory=list)
    detections: List[Detection] = Field(default_factory=list)
    content_categories: List[str] = Field(
        default_factory=list, description="IAB content category IDs"
    )
    processing_time_ms: Optional[float] = Field(
        None, description="Server-side processing duration"
    )
