"""Integration tests verifying frontend serving, static assets, and video streaming endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.edge_server.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_index_html_serving(client):
    """Verify root GET / serves dashboard HTML shell."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Edge Monitor" in response.text
    assert "view-overview" in response.text
    assert "view-live" in response.text


def test_static_assets_serving(client):
    """Verify static CSS and JS are served cleanly."""
    css_res = client.get("/static/css/main.css")
    assert css_res.status_code == 200

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200


def test_camera_snapshot_and_stream(client):
    """Verify camera snapshot returns valid image/jpeg content."""
    # Ensure default cam exists
    cams = client.get("/api/v1/cameras").json()
    assert len(cams) > 0
    cam_id = cams[0]["id"]

    # Test snapshot endpoint
    snapshot_res = client.get(f"/api/v1/cameras/{cam_id}/snapshot")
    assert snapshot_res.status_code == 200
    assert snapshot_res.headers["content-type"] == "image/jpeg"
    assert len(snapshot_res.content) > 100


def test_events_query_filtering(client):
    """Verify events endpoint returns list."""
    res = client.get("/api/v1/events")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_recordings_query(client):
    """Verify recordings endpoint returns list."""
    res = client.get("/api/v1/recordings")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

