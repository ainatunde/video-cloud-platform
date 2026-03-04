"""Unit tests for YOLO scene detector."""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/ai-analysis'))


def test_cosine_similarity_identical():
    from yolo_scene_detector import YOLOSceneDetector
    detector = YOLOSceneDetector.__new__(YOLOSceneDetector)
    vec = np.array([1.0, 0.0, 0.0])
    assert detector._cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    from yolo_scene_detector import YOLOSceneDetector
    detector = YOLOSceneDetector.__new__(YOLOSceneDetector)
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert detector._cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    from yolo_scene_detector import YOLOSceneDetector
    detector = YOLOSceneDetector.__new__(YOLOSceneDetector)
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    assert detector._cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_parallel_vectors():
    from yolo_scene_detector import YOLOSceneDetector
    detector = YOLOSceneDetector.__new__(YOLOSceneDetector)
    a = np.array([2.0, 0.0, 0.0])
    b = np.array([5.0, 0.0, 0.0])
    assert detector._cosine_similarity(a, b) == pytest.approx(1.0)


def test_cosine_similarity_opposite_vectors():
    from yolo_scene_detector import YOLOSceneDetector
    detector = YOLOSceneDetector.__new__(YOLOSceneDetector)
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    result = detector._cosine_similarity(a, b)
    assert result == pytest.approx(-1.0)
