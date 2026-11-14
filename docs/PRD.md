# PRD.md - Edge-to-Server Anomaly Detection & Object Alert System

**Version:** 1.1
**Date:** 2026-11-07
**Status:** Approved for build (demo deadline: tonight · submission: Monday)
**Author:** [Your Name]

### Revision history
- v1.0: on-device inference on a single edge process.
- v1.1: edge node = capture + stream only; all processing on the server.
  Rules R2/R3 changed to a watch-list with an "unattended" check. Added
  frame-ingest endpoint, per-frame metrics, WAL-mode SQLite, unit tests.

---

## 1. Overview

A two-entity computer-vision system. An **edge node** owns the video input
(webcam, video file, or IP-camera URL) and streams compressed frames over HTTP.
A **server** (the laptop) receives the stream, detects objects with a
lightweight deep-learning model, logs detections to SQLite, evaluates anomaly
rules in real time, raises alerts, and serves an API and dashboard.

**Original target hardware:** Raspberry Pi 4 (2GB) + Pi Camera Module, per
syllabus (Unit-1 edge deployment, Unit-3 edge anomaly detection/CV).

**Actual deployment (faculty-guided deviation):** Pi hardware was unavailable.
Faculty suggested either a web simulation of the Pi or spoofing the collection
step as an API with processing on the laptop as server. This project uses the
second option: the Pi is simulated by a standalone edge-client process (same
laptop or a second device) and the laptop is the server. Attach faculty's
written confirmation in the report.

## 2. Problem Statement

Campuses, labs, and small shops need low-cost anomaly detection (occupancy
spikes, unattended objects). A cheap camera node that only captures and
streams, paired with a local server that does the heavy analysis, keeps the
camera hardware simple and keeps video on a local network rather than a public
cloud.

## 3. Goals & Non-Goals

### 3.1 Goals (MVP)
- G1: Server sustains ≥ 8 FPS detection throughput on laptop CPU (edge streams 5 FPS by default, leaving headroom).
- G2: Persist detection events to SQLite with timestamp and device id.
- G3: Detect 3 anomaly classes in real time: occupancy spike, unexpected object, unattended-object dwell.
- G4: Raise alerts on any anomaly (server console banner + beep, red overlay on the annotated frame, dashboard banner).
- G5: Expose frame ingestion, detection injection (spoofed-data mode) and query via HTTP API.
- G6: Live Streamlit dashboard with the annotated video frame, tables, and chart.
- G7: Measure the cost of the edge→server split: bytes per frame, KB/s, inference ms, end-to-end latency.

### 3.2 Non-Goals
- Face recognition or person identification.
- Multi-camera support (state is keyed by `device_id`, but only one device is tested).
- Cloud-hosted inference (the server is the local laptop; a public tunnel is demo-only).
- Training custom models (pretrained COCO weights).
- Real GPIO hardware (simulated).
- On-device inference on the edge node (documented future work).
- Authentication (demo only; do not leave a public tunnel running).

## 4. Users & Use Cases

| User | Use case |
|---|---|
| Demo examiner / faculty | Watch live demo: edge node streams → server detects → anomalies fire → dashboard + DB evidence. |
| Student (author) | Runs the edge node on a video file or phone camera; runs the simulator when no camera/model is available; captures screenshots/video for the report. |
| (Future) Pi owner | Runs `edge/` on a Raspberry Pi; server unchanged. |

## 5. Functional Requirements

### Edge node
| ID | Requirement | Priority |
|---|---|---|
| FR-E1 | `--source` accepts webcam index, video file (auto-loop), or RTSP/HTTP URL | Must |
| FR-E2 | Throttle to `edge.fps` (5), resize to `edge.width` (640), JPEG-encode at `edge.jpeg_quality` (70) | Must |
| FR-E3 | `POST /frames` with `device_id`, `ts`, `seq`; one request in flight; on error back off (max 5 s) and keep sending fresh frames, never crash | Must |
| FR-E4 | Print running stats (frames sent, KB/s, last server response) | Should |
| FR-E5 | Motion gate: skip unchanged frames but send a heartbeat ≥ 1 per second | Could |

### Server
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | `POST /frames` enqueues into a bounded queue (`queue_size` 8); when full, drop the oldest and count `frames_dropped` | Must |
| FR-2 | Worker decodes and detects COCO objects with YOLO26n ONNX (NMS-free head), conf ≥ 0.4 | Must |
| FR-3 | Latest annotated frame (boxes, labels, red overlay during an active alert) served at `GET /frames/latest` | Must |
| FR-4 | Debounced logging: ≤ 1 DB row per class per 2 s of continuous detection, per device | Must |
| FR-5 | Rule R1 occupancy spike: person count > `person_threshold` (3) | Must |
| FR-6 | Rule R2 unexpected object: watch-list class persisting ≥ 5 s | Must |
| FR-7 | Rule R3 dwell: watch-list object unattended ≥ 30 s | Must |
| FR-8 | Alert channels: console banner + platform-aware beep + red overlay + dashboard banner; 10 s cooldown per rule per device | Must |
| FR-9 | API: `POST /frames`, `POST /events` (detection injection), `GET /events /anomalies /stats /health /devices /frames/latest` | Must |
| FR-10 | `scripts/simulator.py` POSTs a scripted 90 s scenario to `/events` reproducing all 3 anomalies without camera or detector | Must |
| FR-11 | Streamlit dashboard: annotated live frame, live tables, person-count chart, alert banner, 2 s refresh; reads the API only | Must |
| FR-12 | Report-grade demo assets: ≥ 90 s screen recording showing edge and server terminals, ≥ 5 screenshots | Must |
| FR-13 | `process_every_n_frames` in the worker if CPU-bound | Should |
| FR-14 | Per-frame metrics (`frame_bytes`, `inference_ms`, `e2e_ms`) stored in `frame_metrics` | Should |
| FR-15 | pytest unit tests for rules using fake timestamps | Should |
| FR-16 | Demo from a second device over LAN or a Cloudflare Tunnel | Could |

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | CPU-only; no GPU, no PyTorch at runtime |
| NFR-2 | Server ≥ 8 FPS at 640×640 on a modern laptop CPU (≥ 5 FPS with frame skipping) |
| NFR-3 | Model ≤ 15 MB on disk; server RAM ≤ 1 GB |
| NFR-4 | One command per process (server, dashboard, edge); no external services |
| NFR-5 | Rules use the edge capture timestamp (`ts`) so queue delay does not distort dwell timing |
| NFR-6 | Edge fails gracefully: missing camera → clear error pointing to file input; server down → retry with backoff |
| NFR-7 | Server runs a single uvicorn worker (in-memory state) |

## 7. Key Decisions & Rationale

| Decision | Choice | Why |
|---|---|---|
| Architecture split | Edge = capture + compress + stream; server = everything else | Matches faculty guidance (spoofed collection, laptop as server); edge stays trivially portable to a Pi |
| Transport | HTTP `POST /frames`, JPEG body, 5 FPS, 640 px, quality 70 | Simplest to debug and demo; works through a tunnel; sequential send gives natural backpressure |
| Server structure | Ingest API + worker thread joined by a bounded drop-oldest queue, one process | Decouples ingest from slow inference; real-time semantics (latest frames win); no shared-memory problems across processes |
| Detector | YOLO26n, ONNX export with `nms=False` | NMS-free head gives `(1,300,6)` output with no post-processing; ~9.8 MB; CPU-oriented |
| Runtime | ONNX Runtime (CPUExecutionProvider) | Cross-platform, no torch dependency |
| Storage | SQLite file DB in WAL mode with busy timeout | Zero-dependency; API/dashboard reads do not block worker writes |
| Ingestion paths | Worker (from frames) and `POST /events` (injected) both call `ingest_detections()` | One rule/DB/alert pipeline, two entry points |
| Rules | Watch-list [backpack, handbag, suitcase]; R3 = unattended | An allow-list or "any still object" rule raises false alerts on chairs, laptops, and misdetections |
| Alerts | Console/beep/overlay/dashboard instead of GPIO | Pi unavailable; GPIO adapter documented |
| Dashboard | Streamlit via API only | Fast live demo UI; works unchanged against a remote server |

## 8. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Examiner asks "where is the edge computing?" | High | State the split honestly: edge = capture/compress/stream, server = inference; show measured bandwidth/latency and the documented edge-inference seam |
| No webcam | Medium | Video-file, phone IP-camera, and simulator modes |
| CPU too slow | Medium | Lower `edge.fps` / `edge.width`, `process_every_n_frames`, drop-oldest queue |
| `demo.mp4` lacks the needed scenes | Medium | Record own clip (4+ people, a bag left on a chair for 40 s); simulator as fallback |
| Live demo crashes | Medium | Pre-record the 90 s video; screenshot every screen |
| Public tunnel exposes an unauthenticated API | Low | Use only during the demo; close afterwards |
| Clock skew between devices distorts latency numbers | Low | Report e2e latency only for same-host runs or NTP-synced devices |
| onnxruntime install issues | Low | Pin Python 3.10-3.12 venv |

## 9. Release Criteria = Acceptance Criteria (see TEST_PLAN.md)

## 10. Open Questions
- Faculty written confirmation of the edge/server split (attach to report).
- Optional: TFLite export benchmark table (stretch).
