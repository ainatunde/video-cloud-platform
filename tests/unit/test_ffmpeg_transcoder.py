"""Unit tests for FFmpeg transcoder."""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/transcoding'))

# _load_preset is a module-level function; set PRESETS_DIR before using
import ffmpeg_transcoder as _ft

_ft.PRESETS_DIR = Path(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets'))
)


def test_load_preset_1080p():
    preset = _ft._load_preset('1080p')
    assert preset['width'] == 1920
    assert preset['height'] == 1080
    assert 'video_bitrate' in preset


def test_load_preset_360p():
    preset = _ft._load_preset('360p')
    assert preset['width'] == 640
    assert preset['height'] == 360


def test_load_preset_720p():
    preset = _ft._load_preset('720p')
    assert preset['width'] == 1280
    assert preset['height'] == 720


def test_load_preset_480p():
    preset = _ft._load_preset('480p')
    assert preset['width'] == 854
    assert preset['height'] == 480


def test_load_preset_invalid():
    with pytest.raises(FileNotFoundError):
        _ft._load_preset('nonexistent_profile')


# ── Path traversal prevention ─────────────────────────────────────────────────

def test_load_preset_path_traversal_dots():
    """Preset names containing path separators must be rejected."""
    with pytest.raises(ValueError):
        _ft._load_preset('../../etc/passwd')


def test_load_preset_path_traversal_slash():
    with pytest.raises(ValueError):
        _ft._load_preset('subdir/1080p')


def test_load_preset_leading_dot():
    """A name starting with '.' must be rejected."""
    with pytest.raises(ValueError):
        _ft._load_preset('.hidden')


def test_load_preset_empty_string():
    with pytest.raises(ValueError):
        _ft._load_preset('')


# ── Bitrate parser ────────────────────────────────────────────────────────────

def test_parse_bitrate_k_suffix():
    assert _ft._parse_bitrate_kbps('4500k') == 4500


def test_parse_bitrate_m_suffix():
    assert _ft._parse_bitrate_kbps('2m') == 2000


def test_parse_bitrate_m_float():
    assert _ft._parse_bitrate_kbps('2.5m') == 2500


def test_parse_bitrate_bare_number():
    assert _ft._parse_bitrate_kbps('1000') == 1000


def test_parse_bitrate_uppercase():
    assert _ft._parse_bitrate_kbps('500K') == 500
