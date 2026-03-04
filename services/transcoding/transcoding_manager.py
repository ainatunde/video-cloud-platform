"""
Transcoding Manager
====================
FastAPI service managing live and VOD FFmpeg transcoding jobs.
Exposes REST endpoints to start, stop, and query transcoding jobs.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ffmpeg_transcoder import FFmpegTranscoder

logger = logging.getLogger(__name__)

DEFAULT_PROFILES = os.environ.get("ABR_PROFILES", "360p,480p,720p,1080p").split(",")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

# In-memory job registry (replace with Redis for multi-replica deployments)
_jobs: Dict[str, Dict[str, Any]] = {}
_transcoder: Optional[FFmpegTranscoder] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _transcoder
    try:
        _transcoder = FFmpegTranscoder()
        logger.info("FFmpegTranscoder initialised")
    except EnvironmentError as exc:
        logger.warning("FFmpeg not available: %s — transcoding endpoints will return 503", exc)
    yield


app = FastAPI(
    title="Transcoding Manager",
    description="FFmpeg ABR transcoding job manager",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Request models ────────────────────────────────────────────────────────────

class LiveJobRequest(BaseModel):
    stream_name: str = Field(..., description="Stream identifier (used for output path)")
    input_url: str = Field(..., description="RTMP or HLS ingest URL")
    profiles: List[str] = Field(default_factory=lambda: DEFAULT_PROFILES)
    scte35_markers: List[float] = Field(default_factory=list, description="PTS timestamps for keyframe forcing")


class VODJobRequest(BaseModel):
    input_file: str = Field(..., description="Absolute path to input video file")
    output_name: str = Field(..., description="Output directory name under OUTPUT_DIR")
    profiles: List[str] = Field(default_factory=lambda: DEFAULT_PROFILES)
    scte35_markers: List[float] = Field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_job(kind: str, **kwargs) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "kind": kind,
        "status": JobStatus.QUEUED,
        "process_pid": None,
        "error": None,
        **kwargs,
    }
    _jobs[job_id] = job
    return job


async def _run_live_job(job: Dict[str, Any]) -> None:
    """Async task that manages a single live transcoding process."""
    job["status"] = JobStatus.RUNNING
    output_dir = f"{OUTPUT_DIR}/{job['stream_name']}"
    try:
        proc = await _transcoder.transcode_live(
            job["input_url"], output_dir, job["profiles"], job.get("scte35_markers")
        )
        job["process_pid"] = proc.pid
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            job["status"] = JobStatus.COMPLETED
        else:
            job["status"] = JobStatus.FAILED
            job["error"] = (stderr or b"").decode(errors="replace")[-500:]
    except asyncio.CancelledError:
        job["status"] = JobStatus.CANCELLED
    except Exception as exc:
        job["status"] = JobStatus.FAILED
        job["error"] = str(exc)
        logger.exception("Live job %s failed", job["job_id"])


class TranscodingManager:
    """Manages the lifecycle of transcoding jobs."""

    async def manage_live_streams(self) -> None:
        """
        Background task: monitors active live streams from SRS and
        starts/stops transcoders accordingly.
        """
        import httpx

        srs_api = os.environ.get("SRS_RTMP_URL", "rtmp://srs:1935").replace(
            "rtmp://", "http://"
        ).split(":1935")[0] + ":1985"

        while True:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{srs_api}/api/v1/streams/")
                    resp.raise_for_status()
                    streams = resp.json().get("streams", [])

                active_names = {s["name"] for s in streams if s.get("publish", {}).get("active")}
                running_names = {
                    j["stream_name"]
                    for j in _jobs.values()
                    if j.get("kind") == "live" and j["status"] == JobStatus.RUNNING
                }

                # Start new transcoders for newly active streams
                for name in active_names - running_names:
                    logger.info("Auto-starting transcoder for stream: %s", name)
                    req = LiveJobRequest(
                        stream_name=name,
                        input_url=f"rtmp://srs:1935/live/{name}",
                    )
                    job = _make_job("live", stream_name=name, input_url=req.input_url,
                                    profiles=req.profiles, scte35_markers=[])
                    asyncio.create_task(_run_live_job(job))

            except Exception as exc:
                logger.warning("manage_live_streams poll error: %s", exc)

            await asyncio.sleep(15)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "ffmpeg_available": _transcoder is not None,
        "active_jobs": sum(1 for j in _jobs.values() if j["status"] == JobStatus.RUNNING),
    }


@app.post("/transcode/live", tags=["jobs"], status_code=202)
async def start_live_job(req: LiveJobRequest) -> Dict[str, Any]:
    """Start a live ABR transcoding job."""
    if _transcoder is None:
        raise HTTPException(status_code=503, detail="FFmpeg not available")
    job = _make_job(
        "live",
        stream_name=req.stream_name,
        input_url=req.input_url,
        profiles=req.profiles,
        scte35_markers=req.scte35_markers,
    )
    asyncio.create_task(_run_live_job(job))
    return {"job_id": job["job_id"], "status": job["status"]}


@app.post("/transcode/vod", tags=["jobs"], status_code=202)
async def start_vod_job(req: VODJobRequest) -> Dict[str, Any]:
    """Start a VOD ABR transcoding job (runs in thread pool)."""
    if _transcoder is None:
        raise HTTPException(status_code=503, detail="FFmpeg not available")
    job = _make_job(
        "vod",
        input_file=req.input_file,
        output_name=req.output_name,
        profiles=req.profiles,
        scte35_markers=req.scte35_markers,
    )

    async def _run():
        job["status"] = JobStatus.RUNNING
        output_dir = f"{OUTPUT_DIR}/{req.output_name}"
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: _transcoder.transcode_vod(
                    req.input_file, output_dir, req.profiles, req.scte35_markers
                ),
            )
            job["status"] = JobStatus.COMPLETED
        except Exception as exc:
            job["status"] = JobStatus.FAILED
            job["error"] = str(exc)
            logger.exception("VOD job %s failed", job["job_id"])

    asyncio.create_task(_run())
    return {"job_id": job["job_id"], "status": job["status"]}


@app.get("/jobs/{job_id}", tags=["jobs"])
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get the status of a transcoding job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/jobs/{job_id}", tags=["jobs"])
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel a running transcoding job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pid = job.get("process_pid")
    if pid and job["status"] == JobStatus.RUNNING:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
            job["status"] = JobStatus.CANCELLED
        except ProcessLookupError:
            job["status"] = JobStatus.COMPLETED  # Already finished

    return {"job_id": job_id, "status": job["status"]}


@app.get("/jobs", tags=["jobs"])
async def list_jobs() -> List[Dict[str, Any]]:
    """List all transcoding jobs."""
    return list(_jobs.values())
