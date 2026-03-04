"""
Threefive SCTE-35 Handler
==========================
Encodes, decodes, and validates SCTE-35 messages using the threefive library.
Also generates HLS EXT-X-DATERANGE tags for SCTE-35 cue delivery over HLS.
"""

from __future__ import annotations

import base64
import binascii
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import threefive

logger = logging.getLogger(__name__)

PTS_FREQ_HZ = 90_000


@dataclass
class Scte35Message:
    """Parsed SCTE-35 message returned by ThreefiveHandler."""
    info_section: Dict[str, Any]
    command: Dict[str, Any]
    descriptors: list
    raw_base64: str


class ThreefiveHandler:
    """
    Thin wrapper around the threefive library for SCTE-35 encode/decode.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Parsing
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_scte35(data: str | bytes, fmt: str = "base64") -> Scte35Message:
        """
        Parse a SCTE-35 message from base64, hex, or binary data.

        Args:
            data:  The encoded SCTE-35 payload.
            fmt:   One of ``"base64"``, ``"hex"``, ``"binary"``.

        Returns:
            Scte35Message with parsed fields.

        Raises:
            ValueError on invalid data or unknown format.
        """
        if fmt == "base64":
            if isinstance(data, bytes):
                data = data.decode()
            cue = threefive.Cue(data)
        elif fmt == "hex":
            if isinstance(data, str):
                data = bytes.fromhex(data)
            b64 = base64.b64encode(data).decode()
            cue = threefive.Cue(b64)
        elif fmt == "binary":
            if isinstance(data, str):
                raise ValueError("binary format requires bytes, not str")
            b64 = base64.b64encode(data).decode()
            cue = threefive.Cue(b64)
        else:
            raise ValueError(f"Unknown format: {fmt!r}. Use 'base64', 'hex', or 'binary'.")

        cue.decode()

        raw_b64 = (
            base64.b64encode(data).decode() if isinstance(data, bytes) else data
        )

        return Scte35Message(
            info_section=cue.info_section.__dict__ if hasattr(cue.info_section, "__dict__") else {},
            command=cue.command.__dict__ if hasattr(cue.command, "__dict__") else {},
            descriptors=[d.__dict__ for d in (cue.descriptors or [])],
            raw_base64=raw_b64,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Encoding
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def encode_splice_insert(
        pts: float,
        duration: float,
        event_id: int = 1,
        out_of_network: bool = True,
        auto_return: bool = True,
    ) -> str:
        """
        Encode a splice_insert SCTE-35 message.

        Args:
            pts:            Presentation timestamp in seconds.
            duration:       Ad break duration in seconds.
            event_id:       Unique splice event ID.
            out_of_network: True = going to ad, False = returning from ad.
            auto_return:    Whether to automatically return to programme.

        Returns:
            Base64-encoded SCTE-35 binary string.
        """
        pts_ticks = int(pts * PTS_FREQ_HZ) & 0x1_FFFF_FFFF
        dur_ticks = int(duration * PTS_FREQ_HZ)

        cue = threefive.Cue()
        cue.info_section.splice_command_type = 0x05  # splice_insert
        cue.command = threefive.SpliceInsert()
        cue.command.splice_event_id = event_id
        cue.command.splice_event_cancel_indicator = False
        cue.command.out_of_network_indicator = out_of_network
        cue.command.program_splice_flag = True
        cue.command.duration_flag = True
        cue.command.splice_immediate_flag = False
        cue.command.time_specified_flag = True
        cue.command.pts_time = pts_ticks

        bd = threefive.BreakDuration()
        bd.auto_return = auto_return
        bd.duration = dur_ticks
        cue.command.break_duration = bd

        cue.encode()
        return cue.bites.hex() if not hasattr(cue, "base64") else base64.b64encode(cue.bites).decode()

    @staticmethod
    def encode_time_signal(pts: float, event_id: int = 1) -> str:
        """
        Encode a time_signal SCTE-35 message (for HLS EXT-X-DATERANGE style cues).

        Args:
            pts:       Presentation timestamp in seconds.
            event_id:  Segmentation event ID (embedded in descriptor).

        Returns:
            Hex-encoded SCTE-35 binary string.
        """
        pts_ticks = int(pts * PTS_FREQ_HZ) & 0x1_FFFF_FFFF

        cue = threefive.Cue()
        cue.info_section.splice_command_type = 0x06  # time_signal
        cue.command = threefive.TimeSignal()
        cue.command.time_specified_flag = True
        cue.command.pts_time = pts_ticks

        cue.encode()
        return cue.bites.hex()

    # ─────────────────────────────────────────────────────────────────────────
    # HLS integration
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_hls_daterange(
        pts: float,
        duration: float,
        event_id: int = 1,
        scte35_cmd: Optional[str] = None,
    ) -> str:
        """
        Generate an HLS EXT-X-DATERANGE tag for SCTE-35 cue delivery.

        Args:
            pts:        Cue-out presentation timestamp (seconds).
            duration:   Ad break duration (seconds).
            event_id:   Splice event ID (used as tag ID).
            scte35_cmd: Optional pre-encoded SCTE-35 base64 string.

        Returns:
            HLS EXT-X-DATERANGE tag string (without leading newline).
        """
        # ISO-8601 timestamp derived from PTS (relative to epoch for simplicity)
        start_date = time.strftime(
            "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(pts)
        )

        tag = (
            f'#EXT-X-DATERANGE:'
            f'ID="splice-{event_id}",'
            f'CLASS="com.apple.hls.interstitial",'
            f'START-DATE="{start_date}",'
            f'DURATION={duration:.3f},'
            f'SCTE35-OUT=0x'
        )

        if scte35_cmd:
            # Append hex-encoded SCTE-35 data
            try:
                raw = base64.b64decode(scte35_cmd)
                tag += raw.hex().upper()
            except Exception:
                tag += scte35_cmd.upper()
        else:
            tag += "00"  # Placeholder

        return tag

    # ─────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def validate_message(msg: str | bytes, fmt: str = "base64") -> Dict[str, Any]:
        """
        Parse and validate a SCTE-35 message.

        Returns:
            {
                "valid": bool,
                "command_type": str | None,
                "errors": [...],
            }
        """
        errors = []
        command_type = None

        try:
            parsed = ThreefiveHandler.parse_scte35(msg, fmt=fmt)
            cmd = parsed.command
            command_type = cmd.get("name") or cmd.get("command_type")

            if not parsed.info_section:
                errors.append("Empty info_section")
            if command_type is None:
                errors.append("Unknown command type")

        except Exception as exc:
            errors.append(str(exc))

        return {
            "valid": len(errors) == 0,
            "command_type": command_type,
            "errors": errors,
        }
