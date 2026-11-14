# System Diagrams (Archify)

Native standalone interactive diagrams generated directly from the codebase architecture, pipeline measurements, database schema, anomaly rules, and runtime component interactions.

| # | Type | Diagram | Output File | Description |
|---|---|---|---|---|
| 1 | `architecture` | [System Architecture](system-architecture.html) | `system-architecture.html` | Edge capture node, FastAPI ingest API (`X-API-Key` + `202 Accepted`), bounded queue, YOLO26n ONNX, tracker, rules, SQLite WAL, and dual React Vite consoles (`:5173`, `:5174`). |
| 2 | `architecture` | [Runtime Component Interaction & Roles](agent-interaction.html) | `agent-interaction.html` | Runtime component interaction map across capture, FastAPI ingest, worker loop, `ONNXRuntimeDetector`, `Tracker`, `RuleEngine`, SQLite WAL, and React consoles. |
| 3 | `workflow` | [Pipeline Workflow](pipeline-workflow.html) | `pipeline-workflow.html` | Multi-lane workflow across Edge, Ingest (`X-API-Key`, `<=2MB`, `202 Accepted`), CV & Rules (hysteresis `0.40`/`0.30`, `owner_id`, `(rule, track_id)` cooldown), and Persistence/UI phases. |
| 4 | `sequence` | [Ingestion Sequence](ingest-sequence.html) | `ingest-sequence.html` | Asynchronous frame ingestion (`202 Accepted`), drop-oldest queueing, worker detection, `(rule, track_id)` evaluation, and dashboard polling sequence. |
| 5 | `dataflow` | [Pipeline Dataflow](pipeline-dataflow.html) | `pipeline-dataflow.html` | Data transformations: BGR arrays → JPEG buffers → ONNX tensors → BBoxes → `Track` objects (`track_id`, `owner_id`) → `Anomaly` alerts & SQLite tables. |
| 6 | `lifecycle` | [Anomaly Lifecycle](anomaly-lifecycle.html) | `anomaly-lifecycle.html` | State machine: detection (`conf>=0.40`, stay `>=0.30`) → `owner_id` binding → unattended dwell → 15s occlusion survival → R2 (5s) → R3 (30s) → owner return RESET to `0s`. |
| 7 | `erd` | [Database Schema](database-schema.html) | `database-schema.html` | Actual 3-table SQLite WAL schema in `server/db.py`: `events`, `anomalies`, and `frame_metrics` (no `devices` table, no foreign keys; logical `device_id` correlation). |
| 8 | `tree` | [Repository Structure](project-structure.html) | `project-structure.html` | Hierarchical module breakdown of `edge/`, `server/`, `frontend/`, `scripts/`, `tests/`, `data/`, and `docs/`. |
| 9 | `class` | [Object Model](object-model.html) | `object-model.html` | Actual Python classes & dataclasses: `VideoSource`, `EdgeEmitterController`, `ONNXRuntimeDetector`, `DeviceState`, `RuleEngine`, `Tracker`, `Track`, and `Anomaly`. |
| 10 | `timeline` | [Incident Timeline](incident-timeline.html) | `incident-timeline.html` | Proportional timeline of owner-bound dwell tracking, passerby & wind-nudge immunity, 4s occlusion continuity, R2/R3 escalation, and owner return RESET to `0s`. |
| 11 | `waterfall` | [Frame Latency Waterfall](frame-latency.html) | `frame-latency.html` | 80.93ms measured E2E & 59.19ms measured ONNX inference from `events.db` (60s @ 640px, 5 FPS); all other sub-spans labeled estimated. |
| 12 | `sequence` | [Auth & Ingest Security](auth-and-ingest-security.html) | `auth-and-ingest-security.html` | 6-layer security sequence: CORS origin gate, `X-API-Key` validation, `Content-Length <= 2 MB` pre-read check, JPEG SOF `<= 4096×4096` guard, and `EdgeConfigUpdate` bounds/source validation. |
