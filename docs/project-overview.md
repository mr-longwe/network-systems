# Project Overview: Local Edge Video Monitoring System

## 1. Executive Summary

The **Local Edge Video Monitoring System** is an edge-computing solution engineered to ingest, process, detect motion, record events, and monitor video streams originating from network-connected devices (primarily Android smartphones acting as RTSP IP cameras).

Operating locally on a Windows edge server connected to a local area network, the system delivers real-time situational awareness through a browser dashboard without dependency on proprietary cloud subscriptions, ensuring high privacy, minimal latency, and full data sovereignty.

## 2. Core Architectural Philosophy

> **"Cameras produce video. The network transports it. The edge server manages it. The browser presents it."**

The architecture strictly adheres to a **modular monolithic design**:
- Single process deployment minimizing container overhead on constrained hardware (Intel Core i5-1035G1, 8 GB RAM).
- Dedicated internal modules with well-defined interfaces and responsibilities.
- Clean separation between video acquisition, frame processing, storage orchestration, and web presentation.

## 3. High-Level Objectives

1. **Local Edge Server Deployment**: Lightweight, resilient FastAPI application hosting both API and monitoring web client.
2. **RTSP Stream Ingestion**: Reliable multi-stream ingestion from Android network cameras over local Wi-Fi.
3. **Computer Vision & Motion Detection**: Real-time frame difference/contour detection running at controlled processing FPS to preserve CPU/RAM.
4. **Automated Event-Triggered Recording**: Immediate clip capture upon motion detection with configurable post-motion padding and local MP4/AVI storage.
5. **Metadata Persistence**: Relational SQLite storage capturing camera states, event logs, recording paths, and system health metrics.
6. **Industrial-Minimalist Dark Dashboard**: Responsive web interface supporting desktop, tablet, and mobile browsers.
7. **Secure Remote Access**: Incremental expansion to encrypted remote monitoring via VPN (WireGuard/Tailscale).

## 4. Key Milestones & Phases

- **Phase 1 — Application Foundation**: Virtualenv, dependency management, FastAPI application lifecycle, and health endpoints.
- **Phase 2 — Frontend Foundation**: Design tokens, responsive CSS grid/flexbox layouts, desktop sidebar, mobile navigation, and UI views.
- **Phase 3 — Backend Integration**: Live system telemetry, dynamic camera status, and API contract implementation.
- **Phase 4 — Camera Integration**: RTSP stream ingestion, stream decoding, and MJPEG browser streaming.
- **Phase 5 — Motion Detection**: OpenCV background subtraction/delta analysis, threshold tuning, and event generation.
- **Phase 6 — Recording and Storage**: VideoWriter pipeline, storage indexing, metadata management, and video playback.
- **Phase 7 — Multi-Camera Orchestration**: Concurrency handling, multi-stream load balancing, and laptop performance profiling.
- **Phase 8 — Reliability & Security**: Automatic reconnection loops, failure mitigation, auth guards, and retention policies.
- **Phase 9 — Remote Monitoring & Access**: VPN configuration and low-bandwidth optimizations.

