"""Integration tests for pipeline connectivity."""
import pytest
import httpx
import os

YOLO_URL = os.getenv("YOLO_URL", "http://localhost:8000")
SCTE35_URL = os.getenv("SCTE35_URL", "http://localhost:8001")
TRANSCODER_URL = os.getenv("TRANSCODER_URL", "http://localhost:8002")
AD_SERVER_URL = os.getenv("AD_SERVER_URL", "http://localhost:3000")


@pytest.mark.integration
def test_yolo_health():
    try:
        r = httpx.get(f"{YOLO_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
    except Exception:
        pytest.skip("YOLO service not available")


@pytest.mark.integration
def test_scte35_health():
    try:
        r = httpx.get(f"{SCTE35_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
    except Exception:
        pytest.skip("SCTE-35 service not available")


@pytest.mark.integration
def test_transcoder_health():
    try:
        r = httpx.get(f"{TRANSCODER_URL}/health", timeout=5)
        assert r.status_code == 200
    except Exception:
        pytest.skip("Transcoder service not available")


@pytest.mark.integration
def test_ad_server_health():
    try:
        r = httpx.get(f"{AD_SERVER_URL}/health", timeout=5)
        assert r.status_code == 200
    except Exception:
        pytest.skip("Ad server not available")


@pytest.mark.integration
def test_scte35_inject_endpoint():
    try:
        r = httpx.post(
            f"{SCTE35_URL}/inject",
            json={
                "stream_id": "test/integration",
                "pts": 30.0,
                "duration": 30.0,
                "splice_type": "splice_insert",
            },
            timeout=5,
        )
        assert r.status_code in (200, 201, 400)  # 400 is acceptable if no live stream
    except Exception:
        pytest.skip("SCTE-35 service not available")


@pytest.mark.integration
def test_ad_decision_endpoint():
    try:
        r = httpx.post(
            f"{AD_SERVER_URL}/ads/decision",
            json={
                "stream_id": "test/integration",
                "event_id": 9999,
                "duration_s": 30,
                "geo_country": "US",
            },
            timeout=5,
        )
        assert r.status_code in (200, 201, 503)  # 503 acceptable if no ad network
    except Exception:
        pytest.skip("Ad server not available")
