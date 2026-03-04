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
