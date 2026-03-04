"""
Manifest Generator
==================
Generates and mutates HLS and DASH manifests, including injection of
SCTE-35 EXT-X-DATERANGE tags and generation of master playlists.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bandwidth values for each ABR profile (used in EXT-X-STREAM-INF)
_PROFILE_BANDWIDTH: Dict[str, int] = {
    "1080p": 4_700_000,
    "720p":  2_628_000,
    "480p":  1_128_000,
    "360p":    596_000,
}

_PROFILE_RESOLUTION: Dict[str, str] = {
    "1080p": "1920x1080",
    "720p":  "1280x720",
    "480p":  "854x480",
    "360p":  "640x360",
}


class ManifestGenerator:
    """
    Generates HLS master playlists, injects SCTE-35 tags, and builds DASH MPDs.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # HLS master playlist
    # ─────────────────────────────────────────────────────────────────────────

    def generate_hls_master(
        self,
        streams: List[Dict[str, Any]],
        base_url: str,
    ) -> str:
        """
        Generate a HLS master playlist (master.m3u8) string.

        Args:
            streams:   List of dicts with keys: profile, path (relative).
            base_url:  CDN/origin URL prefix.

        Returns:
            master.m3u8 content as a string.
        """
        lines = ["#EXTM3U", "#EXT-X-VERSION:6", ""]

        for s in streams:
            profile = s.get("profile", "")
            path = s.get("path", f"{profile}/index.m3u8")
            bandwidth = _PROFILE_BANDWIDTH.get(profile, 1_000_000)
            resolution = _PROFILE_RESOLUTION.get(profile, "")
            url = f"{base_url}/{path}" if base_url else path

            si_attrs = f"BANDWIDTH={bandwidth}"
            if resolution:
                si_attrs += f",RESOLUTION={resolution}"
            si_attrs += ',CODECS="avc1.42e01e,mp4a.40.2"'

            lines.append(f"#EXT-X-STREAM-INF:{si_attrs}")
            lines.append(url)

        return "\n".join(lines) + "\n"

    # ─────────────────────────────────────────────────────────────────────────
    # SCTE-35 EXT-X-DATERANGE injection
    # ─────────────────────────────────────────────────────────────────────────

    def inject_scte35_into_hls(
        self,
        manifest_path: str,
        markers: List[Dict[str, Any]],
    ) -> None:
        """
        Inject EXT-X-DATERANGE tags into an existing HLS playlist file.

        Each marker dict should contain:
        - ``start_date``:  ISO-8601 timestamp string
        - ``duration``:    Ad break duration in seconds
        - ``event_id``:    Splice event ID
        - ``scte35_out``:  Optional hex-encoded SCTE-35 binary (no '0x' prefix)

        The tags are inserted after the first ``#EXT-X-TARGETDURATION`` line.

        Args:
            manifest_path: Absolute path to the .m3u8 file.
            markers:       List of SCTE-35 marker dicts.
        """
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        content = path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        daterange_tags = []
        for m in markers:
            event_id = m.get("event_id", 1)
            start_date = m.get("start_date", "1970-01-01T00:00:00.000Z")
            duration = float(m.get("duration", 30))

            tag = (
                f'#EXT-X-DATERANGE:'
                f'ID="splice-{event_id}",'
                f'CLASS="com.apple.hls.interstitial",'
                f'START-DATE="{start_date}",'
                f'DURATION={duration:.3f}'
            )
            scte35_out = m.get("scte35_out")
            if scte35_out:
                tag += f",SCTE35-OUT=0x{scte35_out.upper()}"

            daterange_tags.append(tag + "\n")

        # Insert after EXT-X-TARGETDURATION (or after the first line)
        insert_at = 1
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-TARGETDURATION"):
                insert_at = i + 1
                break

        for j, tag_line in enumerate(daterange_tags):
            lines.insert(insert_at + j, tag_line)

        path.write_text("".join(lines), encoding="utf-8")
        logger.info(
            "Injected %d SCTE-35 EXT-X-DATERANGE tags into %s",
            len(markers), manifest_path,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DASH MPD generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate_dash_mpd(
        self,
        streams: List[Dict[str, Any]],
        base_url: str,
        min_buffer_time: float = 6.0,
    ) -> str:
        """
        Generate a minimal MPEG-DASH MPD (Media Presentation Description).

        Args:
            streams:          List of dicts with keys: profile, init, template.
            base_url:         CDN/origin URL prefix.
            min_buffer_time:  Minimum buffer time in seconds.

        Returns:
            MPD XML string.
        """
        indent = "  "
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"',
            '     profiles="urn:mpeg:dash:profile:isoff-live:2011"',
            '     type="dynamic"',
            f'     minBufferTime="PT{min_buffer_time:.1f}S"',
            '     availabilityStartTime="1970-01-01T00:00:00Z">',
            f'{indent}<Period id="1" start="PT0S">',
        ]

        for s in streams:
            profile = s.get("profile", "")
            bandwidth = _PROFILE_BANDWIDTH.get(profile, 1_000_000)
            resolution = _PROFILE_RESOLUTION.get(profile, "640x360")
            width, height = resolution.split("x")
            init = s.get("init", f"{profile}/init.mp4")
            template = s.get("template", f"{profile}/$Number$.m4s")

            lines += [
                f'{indent*2}<AdaptationSet mimeType="video/mp4" codecs="avc1.42e01e"',
                f'{indent*3}segmentAlignment="true" startWithSAP="1">',
                f'{indent*3}<Representation id="{profile}" bandwidth="{bandwidth}"',
                f'{indent*4}width="{width}" height="{height}">',
                f'{indent*4}<SegmentTemplate',
                f'{indent*5}initialization="{base_url}/{init}"',
                f'{indent*5}media="{base_url}/{template}"',
                f'{indent*5}startNumber="1" duration="540000" timescale="90000"/>',
                f'{indent*3}</Representation>',
                f'{indent*2}</AdaptationSet>',
            ]

        lines += [
            f'{indent}</Period>',
            '</MPD>',
        ]

        return "\n".join(lines) + "\n"
