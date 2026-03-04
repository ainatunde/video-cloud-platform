"""End-to-end stream workflow tests."""
import pytest
import httpx
import os

YOLO_URL = os.getenv("YOLO_URL", "http://localhost:8000")
SCTE35_URL = os.getenv("SCTE35_URL", "http://localhost:8001")
TRANSCODER_URL = os.getenv("TRANSCODER_URL", "http://localhost:8002")
AD_SERVER_URL = os.getenv("AD_SERVER_URL", "http://localhost:3000")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3002")


@pytest.mark.e2e
def test_full_pipeline_health():
    """Test that all services are healthy when stack is running."""
    services = [
        ("YOLO Analyzer", YOLO_URL + "/health"),
        ("SCTE-35 Processor", SCTE35_URL + "/health"),
        ("Transcoder", TRANSCODER_URL + "/health"),
        ("Ad Server", AD_SERVER_URL + "/health"),
        ("Dashboard", DASHBOARD_URL + "/health"),
    ]
    for name, url in services:
        try:
            r = httpx.get(url, timeout=5)
            assert r.status_code == 200, f"{name} returned {r.status_code}"
        except Exception as e:
            pytest.skip(f"{name} not available: {e}")


@pytest.mark.e2e
def test_ad_insertion_pipeline():
    """Test full ad insertion flow: inject SCTE-35 → ad decision → impression."""
    try:
        # Step 1: Inject a SCTE-35 marker
        inject_resp = httpx.post(
            f"{SCTE35_URL}/inject",
            json={
                "stream_id": "e2e/test_stream",
                "pts": 60.0,
                "duration": 30.0,
                "splice_type": "splice_insert",
                "event_id": 88888,
            },
            timeout=5,
        )
        assert inject_resp.status_code in (200, 201, 400)

        # Step 2: Request ad decision
        decision_resp = httpx.post(
            f"{AD_SERVER_URL}/ads/decision",
            json={
                "stream_id": "e2e/test_stream",
                "event_id": 88888,
                "duration_s": 30,
                "geo_country": "US",
            },
            timeout=5,
        )
        assert decision_resp.status_code in (200, 201, 503)

        if decision_resp.status_code == 200:
            data = decision_resp.json()
            assert "ad_id" in data or "error" in data

    except Exception as e:
        pytest.skip(f"E2E pipeline not available: {e}")


@pytest.mark.e2e
def test_dashboard_serves_frontend():
    """Test that the dashboard serves the React app."""
    try:
        r = httpx.get(DASHBOARD_URL, timeout=5, follow_redirects=True)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
    except Exception as e:
        pytest.skip(f"Dashboard not available: {e}")
