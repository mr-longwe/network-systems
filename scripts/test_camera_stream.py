"""RTSP Camera Stream connectivity diagnostic and latency benchmark utility."""

import sys
import time
import socket
import argparse
from urllib.parse import urlparse
import cv2


def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """Test TCP socket reachability."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"[!] TCP connection to {host}:{port} failed: {e}")
        return False


def test_rtsp_stream(url: str, duration_seconds: int = 10):
    """Attempt OpenCV VideoCapture on RTSP stream and measure incoming FPS and resolution."""
    print("=" * 60)
    print(f"RTSP STREAM DIAGNOSTIC: {url}")
    print("=" * 60)

    # Parse host & port if standard URL
    if "://" in url:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (554 if parsed.scheme == "rtsp" else 8080)
        print(f"[*] Testing network socket reachability ({host}:{port})...")
        if not check_tcp_port(host, port):
            print(f"[!] Warning: Host {host}:{port} is unreachable. Check phone Wi-Fi connection.")
            return False
        print(f"[+] TCP socket reachable to {host}:{port}")

    print("[*] Opening stream with OpenCV VideoCapture...")
    start_open = time.time()
    cap = cv2.VideoCapture(url)
    open_duration = time.time() - start_open

    if not cap.isOpened():
        print(f"[!] Failed to open video stream at {url} (took {open_duration:.2f}s)")
        print("[!] Ensure RTSP server is active on your Android phone and firewall permits incoming traffic.")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_prop = cap.get(cv2.CAP_PROP_FPS)

    print(f"[+] Stream opened successfully in {open_duration:.2f}s!")
    print(f"    - Resolution: {width}x{height}")
    print(f"    - Reported Stream FPS: {fps_prop}")
    print(f"[*] Reading frames for {duration_seconds} seconds to measure throughput...")

    frame_count = 0
    start_test = time.time()
    last_frame_time = start_test

    while time.time() - start_test < duration_seconds:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("[!] Frame read failed or stream stalled")
            time.sleep(0.05)
            continue
        frame_count += 1
        last_frame_time = time.time()

    cap.release()
    total_time = time.time() - start_test
    actual_fps = round(frame_count / total_time, 2) if total_time > 0 else 0

    print("-" * 60)
    print(f"[+] Diagnostic complete:")
    print(f"    - Total frames captured: {frame_count}")
    print(f"    - Actual measured FPS:   {actual_fps}")
    print(f"    - Average frame interval: {1000 / actual_fps:.1f} ms" if actual_fps > 0 else "")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test RTSP stream connectivity from an Android camera")
    parser.add_argument("url", nargs="?", default="rtsp://192.168.1.110:8080/h264_pcm.sdp", help="RTSP URL to test")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    args = parser.parse_args()

    test_rtsp_stream(args.url, duration_seconds=args.duration)

