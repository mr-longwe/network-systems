# NETWORK SYSTEMS DEVELOPMENT
## Project Specification
**Project:** Local Edge Video Monitoring System  
**Version:** 1.0  
**Status:** Initial development specification

---

## 1. Project Overview

Develop a locally hosted edge application that receives video streams from network-connected Android devices, processes video feeds, detects motion, records relevant events and provides an accessible browser-based monitoring dashboard.

The system will initially operate on a Windows laptop connected to an existing local network.

The application must support monitoring from both desktop and mobile browsers, with secure remote access introduced in a later development phase.

### Core architectural principle

**Cameras produce video. The network transports it. The edge server manages it. The browser presents it.**

## 2. Project Objectives

1. Establish a functioning local edge server.
2. Connect multiple Android devices as network cameras using RTSP.
3. Ingest and process video streams.
4. Display camera feeds through a browser dashboard.
5. Detect motion and generate timestamped events.
6. Record video when motion is detected.
7. Store recordings and associated metadata.
8. Provide recording search and playback.
9. Support desktop, laptop, tablet and mobile browsers.
10. Establish secure remote monitoring through VPN.

## 3. Initial Deployment Environment

**Edge server**
- Operating system: Windows 10.
- Processor: Intel Core i5-1035G1.
- RAM: 8 GB.
- Storage: SSD and HDD.
- Initial deployment: Local machine.

**Network**
- Existing Airtel 5G/4G fixed wireless access connection.
- Router: Tozed ZLT W304VA PRO.
- Outdoor unit: Tozed ZLT X17M.
- Laptop connected to the router through Ethernet.
- Three Android phones available as camera sources.

**Network baseline**
- Laptop Ethernet link: 1 Gbps negotiated.
- Laptop IPv4: 192.168.1.161.
- Default gateway: 192.168.1.1.
- Gateway connectivity: Successful.

Actual subnet configuration, available storage and network performance must be verified during implementation.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python |
| API framework | FastAPI |
| Application server | Uvicorn |
| Video ingestion | FFmpeg |
| Video processing | OpenCV |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Video transport | HTTP-compatible browser streaming |
| Camera protocol | RTSP |
| Remote connectivity | VPN |

Use a modular monolithic architecture. Avoid microservices, Kubernetes and unnecessary infrastructure during the initial development stages.

## 5. System Architecture

### Video processing pipeline

Android camera devices  
→ Local WLAN/LAN  
→ RTSP ingestion  
→ Edge server  
→ Video decoding  
→ Motion detection  
→ Event management  
→ Video recording  
→ Filesystem and SQLite storage  
→ FastAPI  
→ Browser dashboard

### Main application modules

**Camera Manager**
- Register cameras.
- Maintain camera configuration.
- Monitor connection status.
- Handle stream connection and reconnection.

**Stream Manager**
- Establish RTSP connections.
- Receive and decode video.
- Manage stream lifecycle.
- Report stream errors.

**Video Processor**
- Process incoming frames.
- Control processing frequency.
- Run motion detection.
- Generate motion metadata.

**Event Manager**
- Create timestamped events.
- Associate events with cameras.
- Manage event states and recording triggers.

**Recording Manager**
- Start recording on motion.
- Continue recording for a configurable period after motion stops.
- Save clips to local storage.
- Associate recordings with event metadata.

**Storage Manager**
- Maintain SQLite records.
- Organise recorded video files.
- Track file paths, sizes and timestamps.
- Support future retention policies.

**API Layer**
- Expose camera information.
- Provide system status.
- Expose event information.
- Provide recording metadata.
- Deliver browser-compatible video feeds.

## 6. Dashboard Requirements

The dashboard must use a consistent industrial-minimalist dark interface.

### Visual identity

- Primary background: #050505
- Elevated background: #0A0A0A
- Surface: #101010
- Secondary surface: #151515
- Primary green: #00B84F
- Green hover: #00D15A
- Primary text: #F5F5F5
- Secondary text: #A3A3A3
- Border: #252525
- Warning: #F28B36
- Error: #EF5350
- Information: #4C91E8

Typography:
- Primary: Inter, with system sans-serif fallbacks.
- Technical data: JetBrains Mono, with Consolas fallback.

Use subtle borders, restrained shadows, clear visual hierarchy and consistent spacing.

### Main navigation

1. Overview
2. Live Monitoring
3. Events
4. Recordings
5. Cameras
6. System

### Overview

Display:
- Online cameras.
- Active events.
- Storage utilisation.
- System health.
- Camera preview cards.
- Recent events.
- CPU utilisation.
- Memory utilisation.
- Disk utilisation.
- Network activity.

### Live Monitoring

- Display connected camera feeds.
- Show camera names and connection status.
- Show stream resolution and frame rate where available.
- Support individual camera viewing.
- Provide a low-bandwidth viewing option in a later phase.

### Events

- Display motion events.
- Display camera connection failures.
- Show timestamps and associated cameras.
- Support filtering and event details.

### Recordings

- Search available recordings.
- Filter by camera and date.
- Display recording duration and file size.
- Support browser playback where compatible.

### Cameras

- Register and configure cameras.
- Display connection status.
- View stream information.
- Enable or disable configured cameras.

### System

- Display application health.
- Display resource utilisation.
- Display service status.
- Provide application logs and configuration information.

## 7. Responsive Design Requirements

One frontend application must support desktop and mobile devices.

### Desktop
- Fixed sidebar navigation.
- Multi-column camera layout.
- Dashboard metrics displayed horizontally.
- Events and system resources displayed in supporting panels.

### Mobile
- Compact top navigation.
- Bottom navigation for primary sections.
- Expandable navigation menu.
- Two-column statistics where space allows.
- Single-column camera feeds.
- Full-width event and recording cards.
- Touch-friendly controls.
- Mobile-compatible video playback.

### Initial breakpoints

- Small mobile: 480px and below.
- Mobile/tablet: 481–768px.
- Tablet/compact desktop: 769–1024px.
- Desktop: above 1024px.

Use flexible layouts and fluid sizing rather than relying exclusively on fixed dimensions.

## 8. Video and Recording Requirements

### Initial implementation

- Support one RTSP camera first.
- Expand to three cameras after validating performance.
- Begin with 640×360 or 640×480.
- Begin with approximately 5–10 processing FPS.
- Disable audio initially.
- Avoid unnecessary transcoding.

### Motion-triggered recording

1. Receive video frames.
2. Analyse frames for motion.
3. Generate a motion event.
4. Start recording.
5. Continue recording for a configurable period after motion ends.
6. Finalise the recording.
7. Save recording metadata.

Pre-event buffering is a future enhancement, not an initial requirement.

### Browser video delivery

Browsers cannot natively play RTSP streams.

The edge server must therefore convert or relay incoming streams through a browser-compatible delivery mechanism.

Start with a simple implementation such as MJPEG for local preview, with conservative resolution and frame rate.

Evaluate WebRTC or HLS for subsequent development based on latency, bandwidth and browser compatibility.

## 9. Security Requirements

- Do not expose RTSP camera ports directly to the public internet.
- Use authenticated camera streams where supported.
- Keep camera credentials out of source code.
- Use environment variables for secrets.
- Implement dashboard authentication before remote access.
- Protect API endpoints.
- Use VPN for remote connectivity.
- Use HTTPS where appropriate for remote browser access.
- Validate user input and uploaded/configured data.
- Avoid committing databases, recordings, credentials or environment files to Git.

Remote access must not be considered complete until it has been tested from an external network.

## 10. Resource and Performance Constraints

The application must be designed for the available 8 GB RAM laptop.

Priorities:
- Low memory consumption.
- Controlled CPU utilisation.
- Configurable processing FPS.
- Efficient stream reconnection.
- Minimal unnecessary background processing.
- Storage monitoring.
- Graceful handling of unavailable cameras.

Do not assume the laptop can sustain three simultaneous streams at arbitrary resolutions. Benchmark actual performance before increasing the workload.

## 11. Development Phases

### Phase 1 — Application Foundation
- Create Python virtual environment.
- Install dependencies.
- Establish FastAPI application.
- Implement health endpoint.
- Verify local application access.

### Phase 2 — Frontend Foundation
- Establish CSS design tokens.
- Build responsive application shell.
- Implement desktop navigation.
- Implement mobile navigation.
- Build dashboard sections with placeholder data.

### Phase 3 — Backend Integration
- Define API contracts.
- Connect frontend to FastAPI.
- Replace placeholder system status with actual backend responses.

### Phase 4 — Camera Integration
- Configure first Android RTSP camera.
- Test stream connectivity.
- Implement stream ingestion.
- Display the first live camera feed.

### Phase 5 — Motion Detection
- Implement motion detection.
- Generate timestamped events.
- Display actual events in the dashboard.

### Phase 6 — Recording and Storage
- Implement event-triggered recording.
- Store clips locally.
- Integrate SQLite metadata.
- Implement recording search and playback.

### Phase 7 — Multi-camera Support
- Register additional cameras.
- Implement independent stream management.
- Test multiple simultaneous feeds.
- Measure resource utilisation.

### Phase 8 — Reliability and Security
- Implement reconnection handling.
- Improve error logging.
- Add authentication.
- Test failure scenarios.
- Implement storage management.

### Phase 9 — Remote Monitoring
- Evaluate VPN options.
- Configure secure remote connectivity.
- Test mobile access over an external network.
- Evaluate low-bandwidth video delivery.

## 12. Acceptance Criteria

The project must not be considered complete merely because the interface looks finished.

| Milestone | Acceptance criteria |
|---|---|
| Application foundation | FastAPI starts and health endpoint responds |
| Frontend | Desktop and mobile layouts render correctly |
| API integration | Dashboard displays actual backend responses |
| Camera integration | One Android RTSP stream is successfully received |
| Live monitoring | Stream is visible in a browser |
| Motion detection | Motion generates a timestamped event |
| Recording | Motion produces a playable video file |
| Database | Camera and event metadata persist |
| Multi-camera | Multiple cameras operate simultaneously |
| Security | Authentication and protected remote access work |
| Remote monitoring | Dashboard works from an external mobile network |

## 13. Repository Organisation

```text
network-systems/
├── README.md
├── .gitignore
├── requirements.txt
├── .env.example
├── docs/
│   ├── project-overview.md
│   ├── project-specification.md
│   ├── system-architecture.md
│   └── network-topology.md
├── src/
│   └── edge_server/
├── web/
│   ├── templates/
│   └── static/
│       ├── css/
│       ├── js/
│       └── assets/
├── tests/
├── scripts/
├── research/
└── data/
```

The structure may evolve as the implementation develops. Do not create empty modules merely to fill the directory tree.

Runtime data, recordings, databases and secrets must remain outside version control.

## 14. AI-Assisted Development Instructions

Any AI coding agent working on this project must:

1. Read this specification before making changes.
2. Inspect the existing repository before generating files.
3. Preserve the existing project identity and architecture.
4. Avoid introducing unnecessary dependencies.
5. Explain significant architectural decisions.
6. Generate maintainable, modular code.
7. Include useful comments where implementation details require explanation.
8. Never invent successful tests or claim unimplemented functionality works.
9. Test each milestone before proceeding.
10. Update documentation when implementation decisions change.
11. Keep internal company and commercial product names out of public repository files.
12. Ask before making significant changes to the agreed architecture.

**Development principle:** Build incrementally. Implement, test, document and verify each milestone before moving to the next.

---

**End of specification — Version 1.0**

