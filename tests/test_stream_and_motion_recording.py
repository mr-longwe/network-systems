"""End-to-end integration test verifying stream ingestion, motion detection, and recording pipeline."""

import time
from pathlib import Path
import pytest
from src.edge_server.cameras.manager import camera_manager
from src.edge_server.streams.manager import stream_manager
from src.edge_server.storage.database import db
from src.edge_server.recording.manager import recording_manager


def test_end_to_end_stream_and_motion_recording():
    """Verify live stream ingestion, motion detection, and recording persistence."""
    test_video_path = Path("data/test_feed_motion.mp4").resolve()
    assert test_video_path.exists(), "Synthetic test feed must exist"

    cam_id = "cam-sim-1"
    # Clean up previous run if any
    camera_manager.delete_camera(cam_id)

    # 1. Register camera with test feed source
    camera_manager.register_camera(
        camera_id=cam_id,
        name="Simulated Motion Camera",
        rtsp_url=str(test_video_path),
        enabled=True,
        fps=15,
        resolution="640x480"
    )

    # 2. Wait for worker to initialize and process frames
    worker = stream_manager.get_worker(cam_id)
    assert worker is not None, "Worker should be initialized"

    # Allow worker to loop through frames and detect motion
    max_wait = 6.0
    start = time.time()
    detected_online = False
    detected_motion = False

    while time.time() - start < max_wait:
        if worker.status == "online":
            detected_online = True
        if worker.is_motion:
            detected_motion = True
            break
        time.sleep(0.2)

    assert detected_online, "Camera stream worker should transition to online"
    assert detected_motion, "Motion detector should trigger on the moving object"

    # 3. Verify event is logged in SQLite
    events = db.get_events(camera_id=cam_id, limit=5)
    assert len(events) > 0, "At least one motion event must be recorded in SQLite"
    motion_event = [e for e in events if e["event_type"] == "motion"]
    assert len(motion_event) > 0, "A motion event should be present"

    # 4. Check that recording session was initiated
    recs = db.get_recordings(camera_id=cam_id, limit=5)
    assert len(recs) > 0, "At least one recording must be registered in SQLite"
    rec = recs[0]
    rec_file = Path(rec["file_path"])
    assert rec_file.exists(), f"Recording file must exist on disk: {rec_file}"

    # 5. Clean up camera
    camera_manager.delete_camera(cam_id)
    assert stream_manager.get_worker(cam_id) is None

