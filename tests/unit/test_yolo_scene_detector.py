"""Unit tests for YOLO scene detector."""
import pytest
import numpy as np
import sys
import os
from unittest.mock import MagicMock

# Stub heavy optional dependencies before importing the module under test
for _mod in ("cv2", "ultralytics", "ultralytics.engine", "ultralytics.engine.results"):
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/ai-analysis'))

# Import the module-level function directly (it is not a method of YOLOSceneDetector)
from yolo_scene_detector import _cosine_similarity


def test_cosine_similarity_identical():
    vec = np.array([1.0, 0.0, 0.0])
    assert _cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_parallel_vectors():
    a = np.array([2.0, 0.0, 0.0])
    b = np.array([5.0, 0.0, 0.0])
    assert _cosine_similarity(a, b) == pytest.approx(1.0)


def test_cosine_similarity_opposite_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert _cosine_similarity(a, b) == pytest.approx(-1.0)
