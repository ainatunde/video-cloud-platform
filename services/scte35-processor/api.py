"""
SCTE-35 Processor — FastAPI application
=========================================
Converts AI scene-change events into SCTE-35 splice markers and injects them
into MPEG-TS streams using TSDuck.  Also exposes encode/decode/validate APIs.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scte35_validator import SCTE35Validator
from threefive_handler import ThreefiveHandler
from tsduck_injector import SplicePoint, TSDuckInjector

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_SPLICE_DURATION = float(os.environ.get("SCTE35_SPLICE_DURATION", "30"))
# Restrict TS file operations to this directory (set to "" to disable the check)
TS_BASE_DIR = os.environ.get("TS_BASE_DIR", "/data")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

app = FastAPI(
    title="SCTE-35 Processor",
    description="SCTE-35 splice marker injection and validation service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

_handler = ThreefiveHandler()
_validator = SCTE35Validator()


def _validate_ts_path(path: str) -> None:
    """
    Reject paths that escape the allowed TS_BASE_DIR directory.

    Raises HTTPException(400) on any path traversal attempt.
    """
    if not TS_BASE_DIR:
        return
    try:
        resolved = Path(path).resolve()
        base = Path(TS_BASE_DIR).resolve()
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"File path must be inside {TS_BASE_DIR}",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc


# ── Request / response models ─────────────────────────────────────────────────

class SceneChangeInput(BaseModel):
    timestamp: float = Field(..., description="Stream timestamp in seconds")
    duration: float = Field(DEFAULT_SPLICE_DURATION, description="Ad break duration")
    event_id: int = Field(1, description="Splice event ID")


class InjectRequest(BaseModel):
    input_ts: str = Field(..., description="Path to input .ts file")
    output_ts: str = Field(..., description="Path to write output .ts file")
    scene_changes: List[SceneChangeInput]


class EncodeRequest(BaseModel):
    pts: float
    duration: float = DEFAULT_SPLICE_DURATION
    event_id: int = 1
    command: str = Field("splice_insert", description="splice_insert | time_signal")


class DecodeRequest(BaseModel):
    data: str = Field(..., description="Base64 or hex SCTE-35 payload")
    fmt: str = Field("base64", description="base64 | hex")


class ValidateRequest(BaseModel):
    ts_file: Optional[str] = None
    scte35_data: Optional[str] = None
    fmt: str = "base64"
    command_type: Optional[str] = Field(None, description="splice_insert | time_signal")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/inject", tags=["injection"])
async def inject_markers(req: InjectRequest) -> Dict[str, Any]:
    """Inject SCTE-35 splice_insert markers into an MPEG-TS file."""
    _validate_ts_path(req.input_ts)
    _validate_ts_path(req.output_ts)
    injector = TSDuckInjector()
    splice_points = [
        SplicePoint(
            event_id=sc.event_id,
            pts_seconds=sc.timestamp,
            duration_seconds=sc.duration,
        )
        for sc in req.scene_changes
    ]
    try:
        injector.inject_markers(req.input_ts, req.output_ts, splice_points)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "ok", "markers_injected": len(splice_points), "output": req.output_ts}


@app.post("/encode", tags=["encode_decode"])
async def encode_marker(req: EncodeRequest) -> Dict[str, Any]:
    """Encode a SCTE-35 splice_insert or time_signal message."""
    try:
        if req.command == "splice_insert":
            encoded = _handler.encode_splice_insert(req.pts, req.duration, req.event_id)
        elif req.command == "time_signal":
            encoded = _handler.encode_time_signal(req.pts, req.event_id)
        else:
            raise HTTPException(status_code=422, detail=f"Unknown command: {req.command}")

        hls_tag = _handler.generate_hls_daterange(req.pts, req.duration, req.event_id, encoded)
        return {"encoded": encoded, "hls_daterange_tag": hls_tag}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/decode", tags=["encode_decode"])
async def decode_marker(req: DecodeRequest) -> Dict[str, Any]:
    """Decode a base64 or hex SCTE-35 message."""
    try:
        parsed = _handler.parse_scte35(req.data, fmt=req.fmt)
        return {
            "info_section": parsed.info_section,
            "command": parsed.command,
            "descriptors": parsed.descriptors,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/validate", tags=["validation"])
async def validate(req: ValidateRequest) -> Dict[str, Any]:
    """Validate a SCTE-35 message or an entire MPEG-TS file."""
    if req.ts_file:
        _validate_ts_path(req.ts_file)
        return _validator.generate_validation_report(req.ts_file)

    if req.scte35_data:
        cmd_type = req.command_type or "splice_insert"
        if cmd_type == "time_signal":
            result = _validator.validate_time_signal(req.scte35_data, fmt=req.fmt)
        else:
            result = _validator.validate_splice_insert(req.scte35_data, fmt=req.fmt)
        return {"passed": result.passed, "message": result.message, "details": result.details}

    raise HTTPException(status_code=422, detail="Provide either ts_file or scte35_data")
