"""Camera Manager coordinating registration, configuration, and stream lifecycles."""

import logging
from typing import List, Dict, Any, Optional
from src.edge_server.config import settings
from src.edge_server.storage.database import db
from src.edge_server.streams.manager import stream_manager

logger = logging.getLogger("edge_server.cameras")


class CameraManager:
    """Manages camera hardware registry and connects to stream workers."""

    def __init__(self):
        pass

    def initialize_cameras(self) -> None:
        """Start streams for all enabled cameras stored in SQLite on system boot."""
        cameras = db.get_all_cameras()
        if not cameras:
            # If database is fresh, register default camera slot based on network baseline
            # (Section 3: Three Android phones available as camera sources)
            default_cam = {
                "id": "cam-1",
                "name": "Android Camera 1",
                "rtsp_url": "rtsp://192.168.1.110:8080/h264_pcm.sdp",
                "enabled": 0,  # Initially disabled until user enters their actual phone IP/port
                "status": "offline",
                "resolution": f"{settings.DEFAULT_FRAME_WIDTH}x{settings.DEFAULT_FRAME_HEIGHT}",
                "fps": settings.DEFAULT_FPS
            }
            db.upsert_camera(default_cam)
            cameras = [default_cam]

        for cam in cameras:
            if cam.get("enabled"):
                self.start_camera(cam["id"])

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        """Retrieve all cameras with their live stream metrics."""
        records = db.get_all_cameras()
        results = []
        for r in records:
            cam_id = r["id"]
            worker = stream_manager.get_worker(cam_id)
            cam_data = dict(r)
            if worker:
                cam_data["status"] = worker.status
                cam_data["fps_actual"] = worker.fps_actual
                cam_data["has_motion"] = worker.is_motion
            else:
                cam_data["status"] = "disabled" if not r.get("enabled") else r.get("status", "offline")
                cam_data["fps_actual"] = 0.0
                cam_data["has_motion"] = False
            results.append(cam_data)
        return results

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        record = db.get_camera(camera_id)
        if not record:
            return None
        worker = stream_manager.get_worker(camera_id)
        cam_data = dict(record)
        if worker:
            cam_data["status"] = worker.status
            cam_data["fps_actual"] = worker.fps_actual
            cam_data["has_motion"] = worker.is_motion
        else:
            cam_data["fps_actual"] = 0.0
            cam_data["has_motion"] = False
        return cam_data

    def register_camera(
        self,
        camera_id: str,
        name: str,
        rtsp_url: str,
        enabled: bool = True,
        fps: int = 10,
        resolution: str = "640x480"
    ) -> Dict[str, Any]:
        """Add or update a camera configuration."""
        cam_data = {
            "id": camera_id,
            "name": name,
            "rtsp_url": rtsp_url,
            "enabled": int(enabled),
            "status": "offline",
            "resolution": resolution,
            "fps": fps
        }
        record = db.upsert_camera(cam_data)
        if enabled:
            self.start_camera(camera_id)
        else:
            self.stop_camera(camera_id)
        return record

    def start_camera(self, camera_id: str) -> bool:
        """Start streaming for a camera."""
        cam = db.get_camera(camera_id)
        if not cam:
            return False

        width = settings.DEFAULT_FRAME_WIDTH
        height = settings.DEFAULT_FRAME_HEIGHT
        if "x" in str(cam.get("resolution", "")):
            try:
                parts = cam["resolution"].split("x")
                width, height = int(parts[0]), int(parts[1])
            except Exception:
                pass

        stream_manager.start_stream(
            camera_id=camera_id,
            name=cam["name"],
            rtsp_url=cam["rtsp_url"],
            fps=cam.get("fps", settings.DEFAULT_FPS),
            width=width,
            height=height
        )
        db.update_camera_status(camera_id, "connecting")
        return True

    def stop_camera(self, camera_id: str) -> bool:
        """Stop streaming for a camera."""
        stream_manager.stop_stream(camera_id)
        db.update_camera_status(camera_id, "offline")
        return True

    def delete_camera(self, camera_id: str) -> bool:
        """Stop stream and delete camera record."""
        self.stop_camera(camera_id)
        return db.delete_camera(camera_id)


camera_manager = CameraManager()

