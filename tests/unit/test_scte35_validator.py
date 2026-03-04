"""Unit tests for SCTE-35 validator."""
import pytest
import sys
import os
from unittest.mock import MagicMock

# Stub threefive before importing modules that depend on it
sys.modules.setdefault('threefive', MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/scte35-processor'))


def test_pts_accuracy_within_tolerance():
    from scte35_validator import SCTE35Validator
    v = SCTE35Validator(tolerance_ms=100)
    # 0.05 s difference = 50 ms, within 100 ms tolerance
    assert v.validate_pts_accuracy(1.0, 1.05).passed is True


def test_pts_accuracy_outside_tolerance():
    from scte35_validator import SCTE35Validator
    v = SCTE35Validator(tolerance_ms=100)
    # 0.2 s difference = 200 ms, outside 100 ms tolerance
    assert v.validate_pts_accuracy(1.0, 1.2).passed is False


def test_pts_accuracy_exact_match():
    from scte35_validator import SCTE35Validator
    v = SCTE35Validator(tolerance_ms=100)
    assert v.validate_pts_accuracy(1.0, 1.0).passed is True


def test_pts_accuracy_at_boundary():
    from scte35_validator import SCTE35Validator
    v = SCTE35Validator(tolerance_ms=100)
    # 99 ms difference: well within 100 ms tolerance
    assert v.validate_pts_accuracy(1.0, 1.099).passed is True
    # 200 ms difference: outside tolerance
    assert v.validate_pts_accuracy(1.0, 1.2).passed is False


def test_pts_calculation():
    # 1 second = 90000 PTS ticks
    from tsduck_injector import TSDuckInjector
    injector = TSDuckInjector.__new__(TSDuckInjector)
    assert injector.pts_from_timestamp(1.0) == 90000
    assert injector.pts_from_timestamp(0.0) == 0


def test_pts_calculation_30_seconds():
    from tsduck_injector import TSDuckInjector
    injector = TSDuckInjector.__new__(TSDuckInjector)
    assert injector.pts_from_timestamp(30.0) == 2700000


def test_pts_calculation_fractional():
    from tsduck_injector import TSDuckInjector
    injector = TSDuckInjector.__new__(TSDuckInjector)
    # 0.5 seconds = 45000 PTS ticks
    assert injector.pts_from_timestamp(0.5) == 45000
