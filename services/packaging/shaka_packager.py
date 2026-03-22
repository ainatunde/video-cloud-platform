"""
Shaka Packager Service
=======================
FastAPI wrapper around the Google Shaka Packager CLI for HLS and DASH output.
Handles segment packaging, manifest generation, and SCTE-35 tag injection.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from manifest_generator import ManifestGenerator

logger = logging.getLogger(__name__)

PACKAGER_BIN = os.environ.get("PACKAGER_BIN", "packager")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output")
BASE_URL = os.environ.get("BASE_URL", "http://localhost")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

_manifest_gen = ManifestGenerator()
_packager: Optional[ShakaPackager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _packager
    try:
        _packager = ShakaPackager()
        logger.info("ShakaPackager initialised using binary: %s", PACKAGER_BIN)
    except EnvironmentError as exc:
        logger.warning("Shaka packager not available: %s — packaging endpoints will return 503", exc)
    yield


app = FastAPI(
    title="Shaka Packager Service",
    description="HLS/DASH packaging with SCTE-35 support",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


# ── Models ────────────────────────────────────────────────────────────────────

class InputStream(BaseModel):
    path: str = Field(..., description="Absolute path to the input transport stream")
    language: str = Field("und", description="BCP-47 language code")
    stream_type: str = Field("video", description="video | audio")
    profile_name: str = Field(..., description="ABR profile name, e.g. '720p'")

    @field_validator("profile_name")
    @classmethod
    def _safe_profile_name(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9_\-]+$', v):
            raise ValueError("profile_name must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("path")
    @classmethod
    def _no_traversal_in_path(cls, v: str) -> str:
        if ".." in Path(v).parts:
            raise ValueError("path must not contain '..' components")
        return v


class PackageRequest(BaseModel):
    stream_name: str = Field(..., description="Output directory name under OUTPUT_DIR")
    input_streams: List[InputStream]
    segment_duration: int = Field(6, ge=1, le=60)
    scte35_markers: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of SCTE-35 marker dicts for EXT-X-DATERANGE injection"
    )

    @field_validator("stream_name")
    @classmethod
    def _safe_stream_name(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9_\-]+$', v):
            raise ValueError("stream_name must contain only alphanumeric characters, underscores, and hyphens")
        return v


# ── Shaka Packager wrapper ────────────────────────────────────────────────────

class ShakaPackager:
    """Wraps the Shaka Packager CLI."""

    def __init__(self, packager_bin: str = PACKAGER_BIN) -> None:
        if not shutil.which(packager_bin):
            raise EnvironmentError(
                f"Shaka packager not found at '{packager_bin}'. "
                "See services/packaging/Dockerfile for installation."
            )
        self._bin = packager_bin

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [self._bin] + args
        logger.info("Shaka packager: %s", " ".join(cmd[:6]) + "…")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=True,
        )
        return result

    def package_hls(
        self,
        input_streams: List[InputStream],
        output_dir: str,
        segment_duration: int = 6,
    ) -> str:
        """
        Package input streams into HLS.

        Args:
            input_streams:    List of InputStream objects.
            output_dir:       Directory to write HLS output.
            segment_duration: Target segment duration in seconds.

        Returns:
            Path to the generated master.m3u8 file.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        args: List[str] = []

        for stream in input_streams:
            if stream.stream_type == "video":
                args += [
                    f"in={stream.path},stream=video,"
                    f"segment_template={output_dir}/{stream.profile_name}/seg$Number$.ts,"
                    f"playlist_name={output_dir}/{stream.profile_name}/index.m3u8,"
                    f"iframe_playlist_name={output_dir}/{stream.profile_name}/iframe.m3u8"
                ]
            else:
                args += [
                    f"in={stream.path},stream=audio,"
                    f"segment_template={output_dir}/audio/{stream.language}/seg$Number$.ts,"
                    f"playlist_name={output_dir}/audio/{stream.language}/index.m3u8,"
                    f"lang={stream.language}"
                ]

        args += [
            "--hls_master_playlist_output", f"{output_dir}/master.m3u8",
            "--segment_duration", str(segment_duration),
            "--fragment_duration", str(segment_duration),
        ]

        self._run(args)
        logger.info("HLS packaging complete → %s/master.m3u8", output_dir)
        return f"{output_dir}/master.m3u8"

    def package_dash(
        self,
        input_streams: List[InputStream],
        output_dir: str,
        segment_duration: int = 6,
    ) -> str:
        """
        Package input streams into MPEG-DASH.

        Returns:
            Path to the generated manifest.mpd file.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        args: List[str] = []

        for stream in input_streams:
            if stream.stream_type == "video":
                args += [
                    f"in={stream.path},stream=video,"
                    f"segment_template={output_dir}/{stream.profile_name}/$Number$.m4s,"
                    f"init_segment={output_dir}/{stream.profile_name}/init.mp4"
                ]
            else:
                args += [
                    f"in={stream.path},stream=audio,"
                    f"segment_template={output_dir}/audio/{stream.language}/$Number$.m4s,"
                    f"init_segment={output_dir}/audio/{stream.language}/init.mp4,"
                    f"lang={stream.language}"
                ]

        args += [
            "--mpd_output", f"{output_dir}/manifest.mpd",
            "--segment_duration", str(segment_duration),
            "--fragment_duration", str(segment_duration),
        ]

        self._run(args)
        logger.info("DASH packaging complete → %s/manifest.mpd", output_dir)
        return f"{output_dir}/manifest.mpd"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> Dict[str, Any]:
    return {"status": "ok", "packager_available": _packager is not None}


@app.post("/package/hls", tags=["packaging"])
async def package_hls(req: PackageRequest) -> Dict[str, Any]:
    """Package streams as HLS and optionally inject SCTE-35 EXT-X-DATERANGE tags."""
    if _packager is None:
        raise HTTPException(status_code=503, detail="Shaka packager binary not available")
    output_dir = f"{OUTPUT_DIR}/{req.stream_name}"
    try:
        master_playlist = _packager.package_hls(
            req.input_streams, output_dir, req.segment_duration
        )
        if req.scte35_markers:
            _manifest_gen.inject_scte35_into_hls(master_playlist, req.scte35_markers)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=exc.stderr[-500:]) from exc

    master_url = f"{BASE_URL}/{req.stream_name}/master.m3u8"
    return {"status": "ok", "master_playlist": master_playlist, "master_url": master_url}


@app.post("/package/dash", tags=["packaging"])
async def package_dash(req: PackageRequest) -> Dict[str, Any]:
    """Package streams as MPEG-DASH."""
    if _packager is None:
        raise HTTPException(status_code=503, detail="Shaka packager binary not available")
    output_dir = f"{OUTPUT_DIR}/{req.stream_name}"
    try:
        mpd_path = _packager.package_dash(
            req.input_streams, output_dir, req.segment_duration
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=exc.stderr[-500:]) from exc

    mpd_url = f"{BASE_URL}/{req.stream_name}/manifest.mpd"
    return {"status": "ok", "mpd_path": mpd_path, "mpd_url": mpd_url}
