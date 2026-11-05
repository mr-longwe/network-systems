"""Video recording manager handling clip capture on motion events."""

import os
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import cv2
import numpy as np
from src.edge_server.config import settings
from src.edge_server.storage.database import db

logger = logging.getLogger("edge_server.recording")


class ActiveRecordingSession:
    """Manages an in-progress video recording file stream."""

    def __init__(
        self,
        recording_id: str,
        camera_id: str,
        event_id: str,
        file_path: Path,
        fps: int,
        width: int,
        height: int,
    ):
        self.recording_id = recording_id
        self.camera_id = camera_id
        self.event_id = event_id
        self.file_path = file_path
        self.fps = fps
        self.width = width
        self.height = height
        self.start_wall_time = datetime.now(timezone.utc).isoformat()
        self.start_epoch = time.time()
        self.last_frame_epoch = self.start_epoch
        self.frames_written = 0

        # VideoWriter with mp4v codec
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            str(self.file_path),
            fourcc,
            float(self.fps),
            (self.width, self.height)
        )

    def write_frame(self, frame: np.ndarray) -> None:
        """Write a single frame resized to target dimensions if necessary."""
        if not self.writer.isOpened():
            return
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        self.writer.write(frame)
        self.frames_written += 1
        self.last_frame_epoch = time.time()

    def close(self) -> Dict[str, Any]:
        """Finalize video writer and return metadata."""
        if self.writer and self.writer.isOpened():
            self.writer.release()

        end_wall_time = datetime.now(timezone.utc).isoformat()
        duration_seconds = max(round(time.time() - self.start_epoch, 2), 0.1)
        file_size = self.file_path.stat().st_size if self.file_path.exists() else 0

        return {
            "recording_id": self.recording_id,
            "camera_id": self.camera_id,
            "event_id": self.event_id,
            "file_path": str(self.file_path),
            "file_size_bytes": file_size,
            "duration_seconds": duration_seconds,
            "start_time": self.start_wall_time,
            "end_time": end_wall_time,
            "status": "completed" if file_size > 0 else "failed"
        }


class RecordingManager:
    """Coordinates camera recording sessions triggered by motion events."""

    def __init__(self):
        self.active_sessions: Dict[str, ActiveRecordingSession] = {}

    def is_recording(self, camera_id: str) -> bool:
        return camera_id in self.active_sessions

    def start_recording(
        self,
        camera_id: str,
        event_id: str,
        width: int,
        height: int,
        fps: int = 10,
    ) -> ActiveRecordingSession:
        """Initiate a new recording session on disk and register in SQLite."""
        if camera_id in self.active_sessions:
            return self.active_sessions[camera_id]

        now = datetime.now(timezone.utc)
        date_folder = now.strftime("%Y-%m-%d")
        dest_dir = settings.RECORDINGS_DIR / camera_id / date_folder
        dest_dir.mkdir(parents=True, exist_ok=True)

        rec_id = f"rec_{camera_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        file_name = f"{now.strftime('%H%M%S')}_{event_id}.mp4"
        file_path = dest_dir / file_name

        session = ActiveRecordingSession(
            recording_id=rec_id,
            camera_id=camera_id,
            event_id=event_id,
            file_path=file_path,
            fps=fps,
            width=width,
            height=height
        )

        # Register in SQLite
        db.create_recording({
            "id": rec_id,
            "camera_id": camera_id,
            "event_id": event_id,
            "file_path": str(file_path),
            "file_size_bytes": 0,
            "duration_seconds": 0.0,
            "start_time": session.start_wall_time,
            "end_time": None,
            "status": "recording"
        })

        self.active_sessions[camera_id] = session
        logger.info(f"Started recording {rec_id} for camera {camera_id} at {file_path}")
        return session

    def record_frame(self, camera_id: str, frame: np.ndarray) -> None:
        """Feed a frame to the active session if one exists."""
        session = self.active_sessions.get(camera_id)
        if session:
            session.write_frame(frame)

    def stop_recording(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Stop recording, release file handle, and update database record."""
        session = self.active_sessions.pop(camera_id, None)
        if not session:
            return None

        metadata = session.close()
        db.update_recording(
            metadata["recording_id"],
            file_size_bytes=metadata["file_size_bytes"],
            duration_seconds=metadata["duration_seconds"],
            end_time=metadata["end_time"],
            status=metadata["status"]
        )
        logger.info(f"Stopped recording {metadata['recording_id']} ({metadata['duration_seconds']}s, {metadata['file_size_bytes']} bytes)")
        return metadata


recording_manager = RecordingManager()
