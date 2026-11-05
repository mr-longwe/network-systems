"""Event manager handling state transitions, motion events, and recording triggers."""

import time
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import numpy as np
from src.edge_server.config import settings
from src.edge_server.storage.database import db
from src.edge_server.recording.manager import recording_manager
from src.edge_server.processing.motion import MotionResult

logger = logging.getLogger("edge_server.events")


class CameraEventState:
    """Tracks state and timers for an individual camera stream."""

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.active_event_id: Optional[str] = None
        self.last_motion_time: float = 0.0
        self.event_start_time: float = 0.0
        self.peak_motion_area: int = 0


class EventManager:
    """Coordinates lifecycle of motion and system events across all cameras."""

    def __init__(self):
        self.camera_states: Dict[str, CameraEventState] = {}

    def _get_or_create_state(self, camera_id: str) -> CameraEventState:
        if camera_id not in self.camera_states:
            self.camera_states[camera_id] = CameraEventState(camera_id)
        return self.camera_states[camera_id]

    def handle_motion_result(
        self,
        camera_id: str,
        frame: np.ndarray,
        motion_result: MotionResult,
        width: int,
        height: int,
        fps: int = 10,
    ) -> Optional[str]:
        """
        Evaluate motion result, managing recording triggers and post-motion padding.
        Returns the active event_id if recording is currently underway.
        """
        state = self._get_or_create_state(camera_id)
        now_epoch = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        if motion_result.has_motion:
            state.last_motion_time = now_epoch
            if motion_result.motion_area > state.peak_motion_area:
                state.peak_motion_area = motion_result.motion_area

            # If no event is currently active, start a new one!
            if state.active_event_id is None:
                event_id = f"evt_{camera_id}_{int(now_epoch)}_{uuid.uuid4().hex[:6]}"
                state.active_event_id = event_id
                state.event_start_time = now_epoch

                event_details = json.dumps({
                    "trigger": "motion_detected",
                    "initial_area": motion_result.motion_area,
                    "boxes": motion_result.bounding_boxes
                })

                db.create_event({
                    "id": event_id,
                    "camera_id": camera_id,
                    "event_type": "motion",
                    "start_time": now_iso,
                    "end_time": None,
                    "status": "active",
                    "details": event_details
                })
                logger.info(f"Motion event {event_id} started on camera {camera_id}")

                # Start recording immediately
                recording_manager.start_recording(
                    camera_id=camera_id,
                    event_id=event_id,
                    width=width,
                    height=height,
                    fps=fps
                )

            # Record the frame
            recording_manager.record_frame(camera_id, frame)
            return state.active_event_id

        else:
            # No motion in this frame. Check if we need to continue post-motion padding or finalize.
            if state.active_event_id is not None:
                elapsed_since_motion = now_epoch - state.last_motion_time
                if elapsed_since_motion <= settings.POST_MOTION_RECORD_SECONDS:
                    # Still within post-motion cooldown window: keep recording
                    recording_manager.record_frame(camera_id, frame)
                    return state.active_event_id
                else:
                    # Cooldown expired: finalize the event and recording
                    event_id = state.active_event_id
                    db.update_event_status(event_id, status="completed", end_time=now_iso)
                    recording_manager.stop_recording(camera_id)
                    logger.info(f"Motion event {event_id} on camera {camera_id} finalized")

                    # Reset state
                    state.active_event_id = None
                    state.peak_motion_area = 0

            return None

    def log_connection_event(self, camera_id: str, event_type: str, details: Optional[str] = None) -> None:
        """Log connection state transitions (e.g. connection_lost, connection_restored)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        event_id = f"sys_{camera_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        db.create_event({
            "id": event_id,
            "camera_id": camera_id,
            "event_type": event_type,
            "start_time": now_iso,
            "end_time": now_iso,
            "status": "completed",
            "details": details or event_type
        })
        logger.warning(f"Connection event logged for {camera_id}: {event_type} - {details}")


event_manager = EventManager()
