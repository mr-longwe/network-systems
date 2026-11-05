"""Generate synthetic test video feed with periodic motion for offline validation."""

import os
from pathlib import Path
import cv2
import numpy as np


def generate_test_motion_video(output_path: str = "data/test_feed_motion.mp4", num_frames: int = 150):
    """Create an MP4 video file with simulated motion."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    width, height = 640, 480
    fps = 10
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(dest), fourcc, float(fps), (width, height))

    print(f"[*] Generating {num_frames} frames of simulated test feed to {dest}...")

    # Box motion parameters
    box_x = 50
    box_y = 200
    box_size = 60

    for i in range(num_frames):
        # Base dark background #101010
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (16, 16, 16)

        # Subtle grid lines
        for gx in range(0, width, 80):
            cv2.line(frame, (gx, 0), (gx, height), (28, 28, 28), 1)
        for gy in range(0, height, 60):
            cv2.line(frame, (0, gy), (width, gy), (28, 28, 28), 1)

        # Static text
        cv2.putText(frame, "EDGE VIDEO SYNTHETIC TEST FEED", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)
        cv2.putText(frame, f"FRAME: {i:04d}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

        # Introduce motion between frames 40-90
        if 40 <= i < 90:
            box_x += 8
            # Bright white moving box
            cv2.rectangle(frame, (box_x, box_y), (box_x + box_size, box_y + box_size), (240, 240, 240), -1)
            cv2.putText(frame, "MOTION EVENT SIMULATION", (box_x, box_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        out.write(frame)

    out.release()
    print(f"[+] Successfully generated {dest} ({dest.stat().st_size} bytes)")
    return dest


if __name__ == "__main__":
    generate_test_motion_video()

