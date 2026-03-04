"""Unit tests for SCTE-35 validator."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/scte35-processor'))


def test_pts_accuracy_within_tolerance():
    from scte35_validator import validate_pts_accuracy
    assert validate_pts_accuracy(90000, 90050, tolerance_ms=100) is True


def test_pts_accuracy_outside_tolerance():
    from scte35_validator import validate_pts_accuracy
    assert validate_pts_accuracy(90000, 100000, tolerance_ms=100) is False


def test_pts_accuracy_exact_match():
    from scte35_validator import validate_pts_accuracy
    assert validate_pts_accuracy(90000, 90000, tolerance_ms=100) is True


def test_pts_accuracy_at_boundary():
    from scte35_validator import validate_pts_accuracy
    # tolerance_ms=100 → 9000 PTS ticks (100ms * 90)
    assert validate_pts_accuracy(90000, 99000, tolerance_ms=100) is True
    assert validate_pts_accuracy(90000, 99001, tolerance_ms=100) is False


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
