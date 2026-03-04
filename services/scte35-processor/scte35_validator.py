"""
SCTE-35 Validator
==================
Validates PTS accuracy, splice_insert and time_signal messages, and generates
a comprehensive validation report for a given MPEG-TS file.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from threefive_handler import ThreefiveHandler

logger = logging.getLogger(__name__)

PTS_FREQ_HZ = 90_000
DEFAULT_TOLERANCE_MS = 100  # ±100 ms default PTS tolerance


@dataclass
class ValidationResult:
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class SCTE35Validator:
    """
    Validates SCTE-35 messages and MPEG-TS files for splice accuracy.
    """

    def __init__(self, tolerance_ms: float = DEFAULT_TOLERANCE_MS) -> None:
        self.tolerance_ms = tolerance_ms
        self._handler = ThreefiveHandler()

    # ─────────────────────────────────────────────────────────────────────────
    # PTS accuracy
    # ─────────────────────────────────────────────────────────────────────────

    def validate_pts_accuracy(
        self,
        expected_pts_seconds: float,
        actual_pts_seconds: float,
        tolerance_ms: Optional[float] = None,
    ) -> ValidationResult:
        """
        Check whether the actual PTS is within tolerance of the expected PTS.

        Args:
            expected_pts_seconds: Desired splice PTS in seconds.
            actual_pts_seconds:   Measured PTS from the TS stream.
            tolerance_ms:         Override the instance default tolerance (ms).

        Returns:
            ValidationResult with pass/fail status and delta information.
        """
        tol = tolerance_ms if tolerance_ms is not None else self.tolerance_ms
        delta_ms = abs(expected_pts_seconds - actual_pts_seconds) * 1000

        passed = delta_ms <= tol
        return ValidationResult(
            passed=passed,
            message=(
                f"PTS {'PASS' if passed else 'FAIL'}: "
                f"delta={delta_ms:.2f} ms (tolerance={tol} ms)"
            ),
            details={
                "expected_pts_seconds": expected_pts_seconds,
                "actual_pts_seconds": actual_pts_seconds,
                "delta_ms": round(delta_ms, 3),
                "tolerance_ms": tol,
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # splice_insert validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate_splice_insert(
        self, msg: str, fmt: str = "base64"
    ) -> ValidationResult:
        """
        Validate a splice_insert SCTE-35 message.

        Checks:
        - Message decodes without error
        - Command type is splice_insert (0x05)
        - splice_event_id is non-zero
        - pts_time is present
        - break_duration is present

        Returns:
            ValidationResult.
        """
        errors: List[str] = []
        details: Dict[str, Any] = {}

        try:
            parsed = self._handler.parse_scte35(msg, fmt=fmt)
            cmd = parsed.command
            details["command"] = cmd

            cmd_type = cmd.get("name") or cmd.get("command_type", "")
            if "splice_insert" not in str(cmd_type).lower() and cmd.get("splice_command_type") != 5:
                errors.append(f"Expected splice_insert, got: {cmd_type!r}")

            event_id = cmd.get("splice_event_id", 0)
            if not event_id:
                errors.append("splice_event_id is zero or missing")

            if not cmd.get("time_specified_flag") and not cmd.get("splice_immediate_flag"):
                errors.append("Neither time_specified_flag nor splice_immediate_flag is set")

            if not cmd.get("break_duration") and not cmd.get("duration_flag"):
                errors.append("break_duration / duration_flag missing")

        except Exception as exc:
            errors.append(f"Decode error: {exc}")

        return ValidationResult(
            passed=len(errors) == 0,
            message="splice_insert PASS" if not errors else f"splice_insert FAIL: {'; '.join(errors)}",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # time_signal validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate_time_signal(
        self, msg: str, fmt: str = "base64"
    ) -> ValidationResult:
        """
        Validate a time_signal SCTE-35 message.

        Checks:
        - Decodes without error
        - Command type is time_signal (0x06)
        - pts_time is present

        Returns:
            ValidationResult.
        """
        errors: List[str] = []
        details: Dict[str, Any] = {}

        try:
            parsed = self._handler.parse_scte35(msg, fmt=fmt)
            cmd = parsed.command
            details["command"] = cmd

            cmd_type = cmd.get("name") or cmd.get("command_type", "")
            if "time_signal" not in str(cmd_type).lower() and cmd.get("splice_command_type") != 6:
                errors.append(f"Expected time_signal, got: {cmd_type!r}")

            if not cmd.get("time_specified_flag") and not cmd.get("pts_time"):
                errors.append("pts_time / time_specified_flag missing")

        except Exception as exc:
            errors.append(f"Decode error: {exc}")

        return ValidationResult(
            passed=len(errors) == 0,
            message="time_signal PASS" if not errors else f"time_signal FAIL: {'; '.join(errors)}",
            details=details,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Full file report
    # ─────────────────────────────────────────────────────────────────────────

    def generate_validation_report(self, ts_file: str) -> Dict[str, Any]:
        """
        Scan an MPEG-TS file with ``tsp`` and produce a structured report
        covering all SCTE-35 sections found.

        Args:
            ts_file:  Path to the .ts file.

        Returns:
            {
                "file": str,
                "scte35_sections_found": int,
                "markers": [...],
                "errors": [...],
                "raw_tsp_output": str,
            }
        """
        report: Dict[str, Any] = {
            "file": ts_file,
            "scte35_sections_found": 0,
            "markers": [],
            "errors": [],
            "raw_tsp_output": "",
        }

        try:
            result = subprocess.run(
                ["tsp", "--input", ts_file, "--plugin", "tables", "--scte35", "--output", "/dev/null"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            output = result.stdout + result.stderr
            report["raw_tsp_output"] = output[:2000]

            # Count SCTE-35 sections (heuristic line counting)
            section_count = output.count("splice_info_section")
            report["scte35_sections_found"] = section_count

            if section_count == 0:
                report["errors"].append("No SCTE-35 sections detected in stream")

        except FileNotFoundError:
            report["errors"].append("tsp not installed; install TSDuck to enable TS validation")
        except subprocess.TimeoutExpired:
            report["errors"].append("tsp timed out processing the file")
        except Exception as exc:
            report["errors"].append(str(exc))

        return report
