# System Architecture

## 1. Modular Monolith Architecture

The system is constructed as a modular monolith in Python using FastAPI. A single deployment unit avoids the operational complexity, network latency, and memory overhead of microservices while maintaining strict internal module separation.

```mermaid
flowchart TD
    subgraph VideoSources["Video Ingestion Layer"]
        CAM1["Android Camera 1 (RTSP)"]
        CAM2["Android Camera 2 (RTSP)"]
        CAM3["Android Camera 3 (RTSP)"]
    end

    subgraph EdgeServer["Edge Server (FastAPI + OpenCV)"]
        CM["Camera Manager\n(Registry & State)"]
        SM["Stream Manager\n(RTSP Ingest & Decode)"]
        VP["Video Processor\n(Motion Detection & Analysis)"]
        EM["Event Manager\n(Event State & Triggers)"]
        RM["Recording Manager\n(Video Writer & Clip Persistence)"]
        STM["Storage Manager\n(SQLite & Disk File Registry)"]
        API["FastAPI API & Web Layer\n(REST, MJPEG Feeds, Static UI)"]

        CAM1 -->|RTSP Stream| SM
        CAM2 -->|RTSP Stream| SM
        CAM3 -->|RTSP Stream| SM

        CM -->|Config & Commands| SM
        SM -->|Decoded Frames| VP
        VP -->|Motion Signals & Frames| EM
        EM -->|Trigger Recording| RM
        VP -->|Frame Buffers| RM
        RM -->|Save Clip| STM
        EM -->|Persist Event| STM
        CM -->|Persist Camera| STM
        API -->|Query State / Control| CM
        API -->|Query Events & Clips| STM
        API -->|Fetch Frames for Stream| SM
    end

    subgraph ClientLayer["Presentation Layer (Browsers)"]
        DESK["Desktop Browser\n(Fixed Sidebar & Multi-Grid)"]
        MOB["Mobile Browser\n(Bottom Navigation & Touch UI)"]
        API -->|MJPEG Video Stream| DESK
        API -->|REST API & HTML/CSS/JS| DESK
        API -->|MJPEG Video Stream| MOB
        API -->|REST API & HTML/CSS/JS| MOB
    end
```

## 2. Core Modules & Responsibilities

### Camera Manager (`src.edge_server.cameras`)
- Maintains camera configurations (ID, name, RTSP URL, credentials, status).
- Dispatches connection and disconnection commands to the Stream Manager.
- Monitors camera health and triggers auto-reconnection on stream loss.

### Stream Manager (`src.edge_server.streams`)
- Establishes and manages RTSP connections via OpenCV `cv2.VideoCapture` / FFmpeg.
- Runs thread-safe frame acquisition to prevent buffer lag (grabbing the freshest frame).
- Encodes frames into browser-compatible formats (MJPEG multipart response).
- Gracefully handles timeout, stream drop, and reconnection cycles.

### Video Processor (`src.edge_server.processing`)
- Controls processing frame rate (5–10 FPS) to conserve CPU cycles.
- Applies grayscale conversion, Gaussian blur, and frame differencing / background modeling.
- Detects contours and measures bounding box area against threshold limits.
- Annotates motion bounding boxes for visual verification when motion occurs.

### Event Manager (`src.edge_server.events`)
- Tracks active motion states per camera (idle vs active motion).
- Emits motion start and motion end events with precise timestamps.
- Manages post-motion cooldown periods before signalling recording completion.

### Recording Manager (`src.edge_server.recording`)
- Writes motion-triggered video clips to disk via `cv2.VideoWriter`.
- Continuously records during active motion and appends post-motion duration.
- Finalizes video container files cleanly and informs the Storage Manager.

### Storage Manager (`src.edge_server.storage`)
- Manages SQLite schema and transactions (cameras, events, recordings).
- Organizes disk directory structure: `data/recordings/{camera_id}/{YYYY-MM-DD}/`.
- Tracks disk space utilization and enforces retention policies.

### API & Presentation Layer (`src.edge_server.api`, `web/`)
- Exposes RESTful endpoints for cameras, streams, events, recordings, and system telemetry.
- Delivers MJPEG video streams: `GET /api/v1/cameras/{id}/stream`.
- Serves static assets (CSS, JS) and HTML application shell designed with the industrial-minimalist dark aesthetic.

