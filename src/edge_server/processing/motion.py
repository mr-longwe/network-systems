"""Computer vision motion detection using OpenCV."""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import cv2
import numpy as np
from src.edge_server.config import settings


@dataclass
class MotionResult:
    """Represents the outcome of motion analysis on a single video frame."""
    has_motion: bool
    motion_area: int
    bounding_boxes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    timestamp: float = 0.0


class MotionDetector:
    """
    Lightweight, adaptive motion detection designed for edge server efficiency.
    Uses running average background accumulation and contour thresholding.
    """

    def __init__(
        self,
        min_area: Optional[int] = None,
        threshold_val: Optional[int] = None,
        accum_weight: float = 0.5,
        blur_kernel: Tuple[int, int] = (21, 21),
    ):
        self.min_area = min_area if min_area is not None else settings.MOTION_MIN_AREA
        self.threshold_val = threshold_val if threshold_val is not None else settings.MOTION_THRESHOLD
        self.accum_weight = accum_weight
        self.blur_kernel = blur_kernel
        self.avg_frame: Optional[np.ndarray] = None

    def reset(self) -> None:
        """Reset the background reference model."""
        self.avg_frame = None

    def process_frame(self, frame: np.ndarray, timestamp: float = 0.0) -> MotionResult:
        """
        Analyze a BGR frame for motion.

        Returns a MotionResult containing detection state and bounding boxes.
        """
        if frame is None or frame.size == 0:
            return MotionResult(has_motion=False, motion_area=0, timestamp=timestamp)

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Apply Gaussian Blur to filter out high-frequency noise
        gray = cv2.GaussianBlur(gray, self.blur_kernel, 0)

        # Initialize running average if first frame
        if self.avg_frame is None:
            self.avg_frame = gray.astype("float")
            return MotionResult(has_motion=False, motion_area=0, timestamp=timestamp)

        # Accumulate the weighted average between the current frame and previous average
        cv2.accumulateWeighted(gray, self.avg_frame, self.accum_weight)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg_frame))

        # Threshold the delta image
        _, thresh = cv2.threshold(frame_delta, self.threshold_val, 255, cv2.THRESH_BINARY)
        # Dilate threshold image to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bounding_boxes = []
        total_motion_area = 0

        for c in contours:
            area = cv2.contourArea(c)
            if area >= self.min_area:
                (x, y, w, h) = cv2.boundingRect(c)
                bounding_boxes.append((int(x), int(y), int(w), int(h)))
                total_motion_area += int(area)

        has_motion = len(bounding_boxes) > 0

        return MotionResult(
            has_motion=has_motion,
            motion_area=total_motion_area,
            bounding_boxes=bounding_boxes,
            timestamp=timestamp
        )

    @staticmethod
    def annotate_frame(frame: np.ndarray, motion_result: MotionResult) -> np.ndarray:
        """Draw bounding boxes and status tag on a copy of the frame."""
        annotated = frame.copy()
        for (x, y, w, h) in motion_result.bounding_boxes:
            # Primary green border (#00B84F in BGR is (79, 184, 0))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (79, 184, 0), 2)
            cv2.putText(
                annotated,
                "MOTION",
                (x, max(y - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (79, 184, 0),
                1,
                cv2.LINE_AA,
            )
        return annotated

