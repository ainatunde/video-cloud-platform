"""
FFmpeg Transcoder
=================
Builds FFmpeg command lines for ABR (Adaptive Bitrate) ladder transcoding
of live RTMP streams and VOD files, with SCTE-35 keyframe alignment support.
Supports NVENC, VAAPI, QSV hardware acceleration, with automatic CPU fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Hardware acceleration ─────────────────────────────────────────────────────
HARDWARE_ACCEL = os.environ.get("HARDWARE_ACCEL", "false").lower()
PRESETS_DIR = Path(__file__).parent / "presets"

# Codec map: hardware encoder → (codec, hwaccel_flag)
_HW_CODEC_MAP: Dict[str, tuple[str, str]] = {
    "nvenc":  ("h264_nvenc",  "cuda"),
    "vaapi":  ("h264_vaapi",  "vaapi"),
    "qsv":    ("h264_qsv",    "qsv"),
}


def _load_preset(name: str) -> dict:
    """Load an ABR preset JSON file by name (e.g. '1080p')."""
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {path}")
    with path.open() as fh:
        return json.load(fh)


def _choose_codec() -> tuple[str, Optional[str]]:
    """
    Return (codec_name, hwaccel_type) based on HARDWARE_ACCEL env var.
    Falls back to libx264 if the requested encoder is unavailable.
    """
    if HARDWARE_ACCEL in _HW_CODEC_MAP:
        codec, hwaccel = _HW_CODEC_MAP[HARDWARE_ACCEL]
        # Verify encoder is available in this ffmpeg build
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, check=False
        )
        if codec in result.stdout:
            logger.info("Using hardware encoder: %s (hwaccel=%s)", codec, hwaccel)
            return codec, hwaccel
        logger.warning(
            "Requested encoder %s not available; falling back to libx264", codec
        )
    return "libx264", None


class FFmpegTranscoder:
    """
    Manages FFmpeg processes for live and VOD transcoding.
    """

    def __init__(self) -> None:
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("ffmpeg not found in PATH")
        self._codec, self._hwaccel = _choose_codec()

    # ─────────────────────────────────────────────────────────────────────────
    # Command builders
    # ─────────────────────────────────────────────────────────────────────────

    def build_abr_command(
        self,
        input_url: str,
        output_dir: str,
        profiles: List[str],
        scte35_markers: Optional[List[float]] = None,
        segment_duration: int = 6,
    ) -> List[str]:
        """
        Build an FFmpeg command for ABR ladder output.

        Each profile produces a separate HLS variant stream under output_dir.

        Args:
            input_url:       RTMP/HLS/file input URL.
            output_dir:      Directory to write HLS segments and playlists.
            profiles:        List of preset names (e.g. ['360p','720p','1080p']).
            scte35_markers:  Optional list of PTS seconds to force keyframes at.
            segment_duration: HLS target segment duration in seconds.

        Returns:
            FFmpeg argv list (ready to pass to subprocess).
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        cmd: List[str] = ["ffmpeg", "-y"]

        # Hardware acceleration input flags
        if self._hwaccel:
            cmd += ["-hwaccel", self._hwaccel]

        cmd += [
            "-i", input_url,
            "-loglevel", "warning",
        ]

        # Build force_key_frames expression
        if scte35_markers:
            kf_expr = "+".join(f"eq(t\\,{m:.3f})" for m in scte35_markers)
            cmd += ["-force_key_frames", f"expr:{kf_expr}"]

        # Per-profile video / audio streams
        for idx, profile_name in enumerate(profiles):
            preset = _load_preset(profile_name)
            codec = self._codec

            # Scale filter
            scale = f"scale={preset['width']}:{preset['height']}"
            if self._hwaccel == "vaapi":
                scale = f"format=nv12|vaapi,hwupload,scale_vaapi={preset['width']}:{preset['height']}"

            cmd += [
                "-map", "0:v:0",
                "-map", "0:a:0",
                f"-c:v:{idx}", codec,
                f"-vf:{idx}", scale,
                f"-b:v:{idx}", preset["video_bitrate"],
                f"-maxrate:{idx}", preset["video_bitrate"],
                f"-bufsize:{idx}", str(int(preset["video_bitrate"].rstrip("k")) * 2) + "k",
                f"-profile:v:{idx}", preset.get("profile", "main"),
                f"-level:{idx}", str(preset.get("level", "3.1")),
                f"-preset:{idx}", preset.get("preset", "fast"),
                f"-g:{idx}", str(preset.get("gop_size", 60)),
                f"-r:{idx}", str(preset.get("fps", 30)),
                f"-c:a:{idx}", "aac",
                f"-b:a:{idx}", preset["audio_bitrate"],
                f"-ar:{idx}", "48000",
            ]

        # HLS muxer output
        var_stream_map = " ".join(
            f"v:{i},a:{i},name:{profiles[i]}" for i in range(len(profiles))
        )
        cmd += [
            "-f", "hls",
            "-hls_time", str(segment_duration),
            "-hls_list_size", "10",
            "-hls_flags", "independent_segments+delete_segments+append_list",
            "-hls_segment_type", "mpegts",
            "-hls_segment_filename", f"{output_dir}/%v/seg%03d.ts",
            "-master_pl_name", "master.m3u8",
            "-var_stream_map", var_stream_map,
            f"{output_dir}/%v/index.m3u8",
        ]

        return cmd

    # ─────────────────────────────────────────────────────────────────────────
    # Live transcoding
    # ─────────────────────────────────────────────────────────────────────────

    async def transcode_live(
        self,
        input_url: str,
        output_dir: str,
        profiles: List[str],
        scte35_markers: Optional[List[float]] = None,
    ) -> asyncio.subprocess.Process:
        """
        Start a long-running live ABR transcode as an async subprocess.

        Returns the Process handle so the caller can monitor / terminate it.
        """
        cmd = self.build_abr_command(input_url, output_dir, profiles, scte35_markers)
        logger.info("Starting live transcode: %s", " ".join(cmd[:8]) + "…")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("Live transcode PID %d started", proc.pid)
        return proc

    # ─────────────────────────────────────────────────────────────────────────
    # VOD transcoding
    # ─────────────────────────────────────────────────────────────────────────

    def transcode_vod(
        self,
        input_file: str,
        output_dir: str,
        profiles: List[str],
        scte35_markers: Optional[List[float]] = None,
    ) -> subprocess.CompletedProcess:
        """
        Synchronously transcode a VOD file.  Blocks until FFmpeg exits.

        Args:
            input_file:     Local file path.
            output_dir:     Output directory for HLS segments.
            profiles:       ABR profile names.
            scte35_markers: Optional splice PTS timestamps for keyframe alignment.

        Returns:
            CompletedProcess with returncode, stdout, stderr.

        Raises:
            subprocess.CalledProcessError on FFmpeg failure.
        """
        cmd = self.build_abr_command(input_file, output_dir, profiles, scte35_markers)
        logger.info("Starting VOD transcode for %s → %s", input_file, output_dir)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=3600,
        )
        logger.info("VOD transcode complete (rc=0) for %s", input_file)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Keyframe alignment helper
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def force_keyframe_at_pts(pts_list: List[float]) -> List[str]:
        """
        Build the ``-force_key_frames`` filter fragment for a list of PTS values.

        Usage::

            extra_args = FFmpegTranscoder.force_keyframe_at_pts([30.0, 60.0])
            cmd += extra_args

        Returns:
            List of two strings: ['-force_key_frames', 'expr:...'].
        """
        if not pts_list:
            return []
        expr = "+".join(f"eq(t\\,{t:.3f})" for t in sorted(set(pts_list)))
        return ["-force_key_frames", f"expr:{expr}"]
