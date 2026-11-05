"""Foundation tests verifying Phase 1 application setup and core modules."""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from src.edge_server.main import app
from src.edge_server.processing.motion import MotionDetector
from src.edge_server.storage.database import DatabaseManager


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Verify health endpoint responds with 200 OK and valid schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "cameras_total" in data


def test_system_status_endpoint(client):
    """Verify system telemetry endpoint returns actual host metrics."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "network" in data
    assert data["memory"]["total_mb"] > 0
    assert data["disk"]["total_gb"] > 0


def test_camera_crud_endpoints(client):
    """Verify camera registration and query lifecycle."""
    test_cam = {
        "id": "cam-test-1",
        "name": "Front Yard Camera",
        "rtsp_url": "rtsp://192.168.1.110:8080/h264_pcm.sdp",
        "enabled": False,
        "fps": 10,
        "resolution": "640x480"
    }

    # Register camera
    post_res = client.post("/api/v1/cameras", json=test_cam)
    assert post_res.status_code == 201

    # Fetch camera
    get_res = client.get(f"/api/v1/cameras/{test_cam['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == test_cam["name"]

    # Delete camera
    del_res = client.delete(f"/api/v1/cameras/{test_cam['id']}")
    assert del_res.status_code == 200


def test_motion_detector():
    """Verify OpenCV motion detector identifies frame deltas."""
    detector = MotionDetector(min_area=100, threshold_val=20)

    # Frame 1: Blank black frame
    frame1 = np.zeros((240, 320, 3), dtype=np.uint8)
    res1 = detector.process_frame(frame1)
    assert not res1.has_motion

    # Frame 2: Still identical frame
    res2 = detector.process_frame(frame1)
    assert not res2.has_motion

    # Frame 3: Sudden bright white rectangle (motion)
    frame3 = frame1.copy()
    frame3[50:150, 50:150] = 255
    res3 = detector.process_frame(frame3)
    assert res3.has_motion
    assert res3.motion_area > 0
    assert len(res3.bounding_boxes) > 0


def test_database_persistence(tmp_path):
    """Verify SQLite database table creation and record persistence."""
    test_db_path = tmp_path / "test.db"
    db_mgr = DatabaseManager(db_path=test_db_path)

    db_mgr.upsert_camera({
        "id": "cam-unit",
        "name": "Unit Camera",
        "rtsp_url": "rtsp://localhost:8554/live",
        "enabled": 1,
        "status": "offline",
        "resolution": "640x480",
        "fps": 10
    })

    cam = db_mgr.get_camera("cam-unit")
    assert cam is not None
    assert cam["name"] == "Unit Camera"

