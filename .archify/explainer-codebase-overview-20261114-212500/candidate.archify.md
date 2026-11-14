# How Does the Edge-to-Server Vision Codebase Work? {#codebase-overview}

A stateless edge capture layer streams resized JPEG frames over HTTP to a single-process FastAPI server. One worker thread runs CPU ONNX detection, tracking, and anomaly rules while two React consoles poll telemetry.

- `edge/` owns capture, resize, and JPEG upload with zero inference on-device.
- `server/` unifies frame inference (`POST /frames`) and synthetic events (`POST /events`) through `ingest_detections()`.
- `RuleEngine` evaluates public and home rules per `device_id` using edge capture timestamps (`ts`).
- `frontend/src/` serves both `:5173` Analytics Console and `:5174` Edge Emitter Deck from one React bundle.

@answer scope="Backend, Edge, Frontend, Scripts & Tests (38 files)"
@meta locale=en style=clean

## How do runtime modules connect end to end? {#system-flow}

@architecture id=runtime-topology title="Edge, Server, and Dual-Frontend Runtime Topology"
| edge | Edge Capture | external |
| api | FastAPI Ingest | backend |
| cv | Worker and Rules | backend |
| store | SQLite and Alerts | database |
| ui | React Consoles | frontend |
| edge > api | POST /frames | |
| api > cv | queue(8) | |
| cv > store | anomalies | |
| ui > api | config, /events | |
| api > ui | poll JSON/JPEG | |

@steps id=topology-steps
| edge_step | Edge Capture | `VideoSource` and `EdgeEmitterController` read webcam, MP4, YouTube, or RTSP and upload JPEG frames. | runtime-topology | edge |
| api_step | FastAPI Ingest | `server/app.py` checks `X-API-Key`, 2 MB payload limit, and JPEG SOF dimensions up to 4096px. | runtime-topology | api |
| cv_step | Worker and Rules | `worker.py`, `detector.py`, `tracker.py`, and `rules.py` run CPU ONNX detection and home/public rules. | runtime-topology | cv |
| store_step | SQLite and Alerts | `db.py` persists WAL tables while `alerts.py` and `agent.py` fire webhooks, beeps, and LangGraph triage. | runtime-topology | store |
| ui_step | React Consoles | `AnalyticsApp` (`:5173`) and `EdgeEmitterApp` (`:5174`) poll live telemetry and push runtime config. | runtime-topology | ui |

## How does the codebase organize files across layers? {#module-map}

| Layer | Directory | Core Files | Primary Responsibility |
| --- | --- | --- | --- |
| Backend API & CV | `server/` | `app.py`, `worker.py`, `detector.py`, `pipeline.py` | HTTP endpoints, queue worker, ONNX inference, pipeline lock {good:Core} |
| Tracking & Rules | `server/` | `tracker.py`, `rules.py` | IoU/centroid matching, owner binding, home/public/tamper rules |
| Persistence & Alerts | `server/` | `db.py`, `alerts.py`, `agent.py` | SQLite WAL tables, beep/overlay/HMAC webhook, LangGraph triage |
| Edge Capture | `edge/` | `capture.py`, `controller.py`, `edge_client.py` | Multi-source video reader, embedded emitter thread, standalone CLI |
| React Frontends | `frontend/src/` | `main.jsx`, `AnalyticsApp.jsx`, `EdgeEmitterApp.jsx`, `GlassShell.jsx` | Role routing, live dashboards, custom cursor, animated tabs |
| Tooling & Verification | `scripts/`, `tests/` | `eval.py`, `export_model.py`, `simulator.py`, `test_frontends.js`, `test_rules.py` | Model export, clip evaluation, 90s simulator, Playwright & pytest |

## What happens during frame ingestion vs event injection? {#ingest-sequence}

@sequence id=dual-ingest title="Frame Inference Path vs Direct Event Injection"
| actor edge | Edge Emitter | frontend |
| actor api | FastAPI App | backend |
| actor worker | CV Worker | backend |
| actor pipe | Pipeline & Rules | backend |
| actor db | SQLite & Alerts | database |
| edge | api | POST /frames (JPEG) |
| api | edge | 202 queued | return |
| worker | api | Pop frame from queue(8) |
| worker | pipe | ingest_detections(dets, ts) |
| edge | api | POST /events (JSON) |
| api | pipe | ingest_detections(dets, ts) |
| pipe | db | Debounced events + anomalies |
| pipe | api | Return anomalies | return |

Both entry paths merge inside `ingest_detections()` under `ingest_lock` so `POST /events` tests rules identically to live inference. Frame metrics (`frame_bytes`, `inference_ms`, `e2e_ms`) are recorded only by `worker.py` after `ONNXRuntimeDetector.detect()`.

## Which reference artifacts cover each detail level? {#reference-links}

| Artifact | Path | Best Used For |
| --- | --- | --- |
| Navigable Code Explorer | `docs/CODEBASE_REFERENCE.html` | Interactive file tree, search, signatures, and per-function breakdowns |
| Markdown Reference | `docs/CODEBASE_REFERENCE.md` | Readable offline audit of every file, class, component, and function |
| Knowledge Graph | `graphify-out/graph.html` | Interactive call, import, and community graph across 35 source and doc files |
| Graph Audit Report | `graphify-out/GRAPH_REPORT.md` | God nodes, cross-community couplings, and structural summary |
| Architecture Diagrams | `docs/diagrams/*.html` | 12 focused Archify diagrams covering ERD, sequence, lifecycle, and security |
