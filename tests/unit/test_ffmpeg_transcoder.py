"""Unit tests for FFmpeg transcoder."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/transcoding'))


def test_load_preset_1080p():
    from ffmpeg_transcoder import FFmpegTranscoder
    t = FFmpegTranscoder.__new__(FFmpegTranscoder)
    t.presets_dir = os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets')
    preset = t._load_preset('1080p')
    assert preset['width'] == 1920
    assert preset['height'] == 1080
    assert 'video_bitrate' in preset


def test_load_preset_360p():
    from ffmpeg_transcoder import FFmpegTranscoder
    t = FFmpegTranscoder.__new__(FFmpegTranscoder)
    t.presets_dir = os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets')
    preset = t._load_preset('360p')
    assert preset['width'] == 640
    assert preset['height'] == 360


def test_load_preset_720p():
    from ffmpeg_transcoder import FFmpegTranscoder
    t = FFmpegTranscoder.__new__(FFmpegTranscoder)
    t.presets_dir = os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets')
    preset = t._load_preset('720p')
    assert preset['width'] == 1280
    assert preset['height'] == 720


def test_load_preset_480p():
    from ffmpeg_transcoder import FFmpegTranscoder
    t = FFmpegTranscoder.__new__(FFmpegTranscoder)
    t.presets_dir = os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets')
    preset = t._load_preset('480p')
    assert preset['width'] == 854
    assert preset['height'] == 480


def test_load_preset_invalid():
    from ffmpeg_transcoder import FFmpegTranscoder
    t = FFmpegTranscoder.__new__(FFmpegTranscoder)
    t.presets_dir = os.path.join(os.path.dirname(__file__), '../../services/transcoding/presets')
    with pytest.raises((FileNotFoundError, KeyError, ValueError)):
        t._load_preset('nonexistent_profile')
