"""RTSP Stream ingestion and MJPEG relay engine using OpenCV."""

import os
import time
import threading
import logging
from typing import Dict, Optional, Generator
import cv2
import numpy as np
from src.edge_server.config import settings
from src.edge_server.processing.motion import MotionDetector, MotionResult
from src.edge_server.events.manager import event_manager
from src.edge_server.storage.database import db

logger = logging.getLogger("edge_server.streams")


class CameraStreamWorker:
    """
    Dedicated worker thread per camera.
    Drains RTSP network buffer continuously to prevent lag, executes motion detection,
    and updates the latest processed frame for web consumers.
    """

    def __init__(
        self,
        camera_id: str,
        name: str,
        rtsp_url: str,
        target_fps: int = 10,
        target_width: int = 640,
        target_height: int = 480,
    ):
        self.camera_id = camera_id
        self.name = name
        self.rtsp_url = rtsp_url
        self.target_fps = target_fps
        self.target_width = target_width
        self.target_height = target_height

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self.latest_frame: Optional[np.ndarray] = None
        self.latest_jpeg: Optional[bytes] = None
        self.status: str = "offline"  # 'offline', 'connecting', 'online', 'error'
        self.last_frame_time: float = 0.0
        self.fps_actual: float = 0.0
        self.is_motion: bool = False

        self.motion_detector = MotionDetector(
            min_area=settings.MOTION_MIN_AREA,
            threshold_val=settings.MOTION_THRESHOLD
        )

    def start(self) -> None:
        """Start background worker thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, name=f"stream-{self.camera_id}", daemon=True)
        self.thread.start()
        logger.info(f"Stream worker started for camera {self.camera_id}")

    def stop(self) -> None:
        """Stop background worker thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.status = "offline"
        self._set_placeholder_frame("STREAM STOPPED")
        logger.info(f"Stream worker stopped for camera {self.camera_id}")

    def _set_placeholder_frame(self, message: str) -> None:
        """Render an industrial-minimal dark placeholder card for browser display."""
        w, h = self.target_width, self.target_height
        img = np.zeros((h, w, 3), dtype=np.uint8)
        # Background: #101010 (BGR: 16, 16, 16)
        img[:] = (16, 16, 16)

        # Subtle border: #252525 (BGR: 37, 37, 37)
        cv2.rectangle(img, (2, 2), (w - 3, h - 3), (37, 37, 37), 1)

        # Camera Name: #F5F5F5 (BGR: 245, 245, 245)
        cv2.putText(img, f"CAMERA: {self.name}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 245, 245), 2, cv2.LINE_AA)
        
        # Status / Message: Warning Orange or Gray
        color = (54, 139, 242) if "OFFLINE" in message or "RECONNECTING" in message else (163, 163, 163)
        cv2.putText(img, message, (30, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        
        # Timestamp
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(img, ts, (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)

        _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with self.lock:
            self.latest_frame = img
            self.latest_jpeg = jpeg.tobytes()

    def _run_loop(self) -> None:
        """Main loop: connect to RTSP, decode frames, execute motion detection."""
        reconnect_delay = 2.0
        max_reconnect_delay = 15.0

        while self.running:
            self.status = "connecting"
            db.update_camera_status(self.camera_id, "connecting")
            self._set_placeholder_frame(f"CONNECTING TO {self.camera_id}...")

            # Configure OpenCV VideoCapture options for low latency RTSP over TCP
            # Setting environment or capture flags if supported
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"
            
            # Allow camera index integer for local test webcam or RTSP URL
            source = int(self.rtsp_url) if self.rtsp_url.isdigit() else self.rtsp_url
            cap = cv2.VideoCapture(source)

            # Check if opened successfully
            if not cap.isOpened():
                self.status = "offline"
                db.update_camera_status(self.camera_id, "offline")
                event_manager.log_connection_event(self.camera_id, "connection_failed", f"Failed to connect to {self.rtsp_url}")
                self._set_placeholder_frame("CONNECTION FAILED. RETRYING...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                continue

            # Connected successfully!
            reconnect_delay = 2.0
            self.status = "online"
            db.update_camera_status(self.camera_id, "online")
            event_manager.log_connection_event(self.camera_id, "connection_restored", f"Connected to {self.rtsp_url}")
            logger.info(f"Connected to stream {self.camera_id}")

            # Read stream resolution if available
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.target_width
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.target_height
            self.motion_detector.reset()

            frame_interval = 1.0 / max(self.target_fps, 1)
            last_process_time = 0.0
            consecutive_failures = 0

            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    # If reading from a local test video file, seamlessly loop back to frame 0
                    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if total_frames > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        time.sleep(0.02)
                        continue

                    consecutive_failures += 1
                    if consecutive_failures > 30:
                        logger.warning(f"Excessive read failures on {self.camera_id}. Dropping connection.")
                        break
                    time.sleep(0.01)
                    continue

                consecutive_failures = 0
                now = time.time()

                # Control processing rate to adhere to target FPS
                if now - last_process_time < frame_interval:
                    continue

                # Resize if necessary
                if frame.shape[1] != self.target_width or frame.shape[0] != self.target_height:
                    frame = cv2.resize(frame, (self.target_width, self.target_height))

                # Analyze motion
                motion_res = self.motion_detector.process_frame(frame, timestamp=now)
                self.is_motion = motion_res.has_motion

                # Process recording triggers and event states
                event_manager.handle_motion_result(
                    camera_id=self.camera_id,
                    frame=frame,
                    motion_result=motion_res,
                    width=self.target_width,
                    height=self.target_height,
                    fps=self.target_fps
                )

                # Annotate frame for live view if motion detected
                display_frame = frame
                if motion_res.has_motion:
                    display_frame = MotionDetector.annotate_frame(frame, motion_res)

                # Overlay camera name and timestamp in minimalist style
                cv2.putText(
                    display_frame,
                    f"{self.name} | {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    (10, self.target_height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (245, 245, 245),
                    1,
                    cv2.LINE_AA
                )

                # Encode to JPEG for browser MJPEG streaming
                _, jpeg = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])

                # Update live cache
                with self.lock:
                    self.latest_frame = display_frame
                    self.latest_jpeg = jpeg.tobytes()
                    if self.last_frame_time > 0:
                        self.fps_actual = round(1.0 / max(now - self.last_frame_time, 0.001), 1)
                    self.last_frame_time = now

                last_process_time = now

            # Clean up stream
            cap.release()
            self.status = "offline"
            db.update_camera_status(self.camera_id, "offline")
            event_manager.log_connection_event(self.camera_id, "connection_lost", "Stream ended or disconnected")
            self._set_placeholder_frame("CONNECTION LOST. RECONNECTING...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)


class StreamManager:
    """Manages worker threads and MJPEG stream subscriptions for all cameras."""

    def __init__(self):
        self.workers: Dict[str, CameraStreamWorker] = {}

    def get_worker(self, camera_id: str) -> Optional[CameraStreamWorker]:
        return self.workers.get(camera_id)

    def start_stream(
        self,
        camera_id: str,
        name: str,
        rtsp_url: str,
        fps: int = 10,
        width: int = 640,
        height: int = 480
    ) -> CameraStreamWorker:
        """Create or restart a camera worker stream."""
        if camera_id in self.workers:
            self.stop_stream(camera_id)

        worker = CameraStreamWorker(
            camera_id=camera_id,
            name=name,
            rtsp_url=rtsp_url,
            target_fps=fps,
            target_width=width,
            target_height=height
        )
        self.workers[camera_id] = worker
        worker.start()
        return worker

    def stop_stream(self, camera_id: str) -> None:
        """Stop and remove a camera worker stream."""
        worker = self.workers.pop(camera_id, None)
        if worker:
            worker.stop()

    def get_latest_jpeg(self, camera_id: str) -> bytes:
        """Get the latest frame JPEG bytes or a fallback card."""
        worker = self.workers.get(camera_id)
        if worker and worker.latest_jpeg:
            with worker.lock:
                return worker.latest_jpeg
        
        # If no worker running, produce standalone offline placeholder
        img = np.zeros((settings.DEFAULT_FRAME_HEIGHT, settings.DEFAULT_FRAME_WIDTH, 3), dtype=np.uint8)
        img[:] = (16, 16, 16)
        cv2.putText(img, f"CAMERA: {camera_id}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 245, 245), 2)
        cv2.putText(img, "OFFLINE", (30, settings.DEFAULT_FRAME_HEIGHT // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (54, 139, 242), 2)
        _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return jpeg.tobytes()

    def generate_mjpeg(self, camera_id: str) -> Generator[bytes, None, None]:
        """Generator yielding MJPEG multipart frame stream for HTTP response."""
        frame_delay = 1.0 / max(settings.DEFAULT_FPS, 1)
        while True:
            frame_bytes = self.get_latest_jpeg(camera_id)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n" +
                frame_bytes + b"\r\n"
            )
            time.sleep(frame_delay)


stream_manager = StreamManager()
