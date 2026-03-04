"""
TSDuck SCTE-35 Injector
=======================
Generates TSDuck XML splice-insert descriptors from scene-change events and
injects them into MPEG-TS streams using the ``tsp`` command-line tool.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# PTS clock frequency (90 kHz)
PTS_FREQ_HZ = 90_000


@dataclass
class SplicePoint:
    """Represents a single splice-insert point derived from a scene change."""
    event_id: int
    pts_seconds: float
    duration_seconds: float = 30.0
    auto_return: bool = True


class TSDuckInjector:
    """
    Wraps the TSDuck ``tsp`` command-line tool to inject SCTE-35 markers
    into MPEG-TS files or live streams.
    """

    def __init__(self, tsp_path: str = "tsp") -> None:
        if not shutil.which(tsp_path):
            raise EnvironmentError(
                f"TSDuck 'tsp' not found at '{tsp_path}'. "
                "Install TSDuck: https://tsduck.io/"
            )
        self._tsp = tsp_path

    # ─────────────────────────────────────────────────────────────────────────
    # PTS helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def pts_from_timestamp(ts_seconds: float) -> int:
        """Convert wall-clock seconds to a 90 kHz PTS value."""
        return int(ts_seconds * PTS_FREQ_HZ) & 0x1_FFFF_FFFF  # 33-bit PTS

    @staticmethod
    def duration_from_seconds(seconds: float) -> int:
        """Convert seconds to 90 kHz ticks for use in break_duration."""
        return int(seconds * PTS_FREQ_HZ)

    # ─────────────────────────────────────────────────────────────────────────
    # XML generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate_tsduck_xml(self, splice_points: List[SplicePoint]) -> str:
        """
        Generate a TSDuck XML file describing SCTE-35 splice_insert markers.

        The XML is consumed by the ``tsp --plugin inject`` processor.

        Returns:
            Well-formed XML string.
        """
        root = ET.Element("tsduck")

        for sp in splice_points:
            pts_val = self.pts_from_timestamp(sp.pts_seconds)
            dur_val = self.duration_from_seconds(sp.duration_seconds)

            table = ET.SubElement(root, "splice_info_section")
            table.set("protocol_version", "0")
            table.set("pts_adjustment", "0")
            table.set("tier", "0xFFF")

            cmd = ET.SubElement(table, "splice_insert")
            cmd.set("splice_event_id", str(sp.event_id))
            cmd.set("splice_event_cancel", "false")
            cmd.set("out_of_network", "true")
            cmd.set("unique_program_id", "1")
            cmd.set("avail_num", "0")
            cmd.set("avails_expected", "0")

            # Splice time (programme clock reference)
            splice_time = ET.SubElement(cmd, "splice_time")
            splice_time.set("pts_time", str(pts_val))

            # Break duration
            if sp.duration_seconds > 0:
                bd = ET.SubElement(cmd, "break_duration")
                bd.set("auto_return", "true" if sp.auto_return else "false")
                bd.set("duration", str(dur_val))

        xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'

    # ─────────────────────────────────────────────────────────────────────────
    # Injection
    # ─────────────────────────────────────────────────────────────────────────

    def inject_markers(
        self,
        input_ts: str,
        output_ts: str,
        splice_points: List[SplicePoint],
        scte35_pid: int = 500,
    ) -> subprocess.CompletedProcess:
        """
        Inject SCTE-35 markers into an MPEG-TS file using ``tsp``.

        Args:
            input_ts:      Path to the input .ts file.
            output_ts:     Path to write the output .ts file.
            splice_points: List of SplicePoint objects to inject.
            scte35_pid:    PID to assign to the SCTE-35 stream.

        Returns:
            CompletedProcess with stdout/stderr captured.

        Raises:
            subprocess.CalledProcessError on tsp failure.
        """
        xml_content = self.generate_tsduck_xml(splice_points)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(xml_content)
            xml_path = fh.name

        logger.info(
            "Injecting %d SCTE-35 markers into %s → %s (PID %d)",
            len(splice_points), input_ts, output_ts, scte35_pid,
        )

        cmd = [
            self._tsp,
            "--input", input_ts,
            "--plugin", "inject",
            "--pid", str(scte35_pid),
            "--xml", xml_path,
            "--output", output_ts,
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            logger.info("tsp inject succeeded: %s", result.stdout[:200])
            return result
        except subprocess.CalledProcessError as exc:
            logger.error("tsp inject failed (rc=%d): %s", exc.returncode, exc.stderr)
            raise
        finally:
            Path(xml_path).unlink(missing_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate_markers(self, ts_file: str) -> dict:
        """
        Use ``tsp`` to scan a .ts file and verify SCTE-35 PIDs are present.

        Returns:
            Dict with keys: ``scte35_found``, ``pid_list``, ``raw_output``.
        """
        cmd = [
            self._tsp,
            "--input", ts_file,
            "--plugin", "tables",
            "--all-sections",
            "--scte35",
            "--output", "/dev/null",
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
            scte35_found = "SCTE 35" in output or "splice_info_section" in output
            # Extract PIDs from tsp output (heuristic)
            pid_list = [
                int(token)
                for token in output.split()
                if token.isdigit() and 1 <= int(token) <= 8191
            ]
            return {
                "scte35_found": scte35_found,
                "pid_list": sorted(set(pid_list)),
                "raw_output": output[:1000],
            }
        except subprocess.CalledProcessError as exc:
            logger.error("tsp validate failed: %s", exc.stderr)
            return {"scte35_found": False, "pid_list": [], "raw_output": exc.stderr}
