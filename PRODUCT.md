# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Demo examiners, faculty reviewers, and system operators monitoring live edge-to-server computer-vision anomaly detection on a laptop during live demonstrations and extended monitoring sessions.

## Product Purpose

Provide two decoupled web workspaces over a local FastAPI + YOLO26n ONNX + SQLite pipeline:
- **Analytics Console (`:5173`)**: Consumes live annotated video frames, occupancy timelines, R1/R2/R3 anomaly triggers, detection event logs, connected edge node status, and engine rule configuration.
- **Edge Control Deck (`:5174`)**: Controls the upstream edge node video source (local MP4 scenarios, USB webcam, or custom RTSP/HTTP/YouTube URLs), uplink encoder parameters (FPS, frame width, JPEG quality, device ID), and synthetic R1/R2/R3 event injection for verification.

## Positioning

A transparent edge-capture vs. server-inference split that separates video acquisition and compression from CPU ONNX detection, tracking, and deterministic rule evaluation while keeping every metric (KB/frame, KB/s, queue depth, inference ms, end-to-end ms) observable in real time.

## Operating Context

- Runs locally on a laptop or LAN over HTTP (`localhost:8000` API, `localhost:5173` Analytics Console, `localhost:5174` Edge Control Deck).
- Dual-app runtime router in `frontend/src/main.jsx` serves both consoles from one React 18 + Vite 6 codebase based on port (`:5174`), query parameter (`?app=edge`), or `VITE_APP_ROLE=edge`.
- Used in sustained viewing sessions where eye strain from harsh contrast or decorative dark glass chrome degrades readability.

## Capabilities and Constraints

- Preserve all existing Analytics Console views (`Live Monitor`, `Anomaly Vault` / triggered anomalies, `Detection Ledger` / object detections, `Nodes & Rules`) and all Edge Control Deck views (`Video Source Switcher`, `Encoder & Bandwidth`, `Synthetic Anomaly Injector`).
- Preserve all backend API integrations (`/stats`, `/anomalies`, `/events`, `/devices`, `/health`, `/frames/latest`, `/edge/status`, `/edge/config`, `/edge/frame`, `POST /events`) and optional `X-API-Key` header support (`VITE_API_KEY`).
- Keep deployment mode switching (`GET/POST /mode`) omitted from the UI to keep both workspaces simple and focused.
- Drop the former "RoastGlass" name and coffee-glass identity in favor of plain functional titles ("Analytics Console" and "Edge Control Deck").
- Binding aesthetic constraint from user brief: dull, muted light mode that is easy on the eyes, with a simpler, less cluttered structure (compact metrics strip, cleaner tables, fewer nested boxes).

## Evidence on Hand

- Live API endpoints and SQLite schemas documented in `docs/API_SPEC.md`, `docs/PRD.md`, and `server/app.py`.
- Local sample video clips in `data/*.mp4` and YOLOv26n ONNX detector (`yolo26n.onnx`).
- Existing Playwright smoke harness in `scripts/test_frontends.js`.

## Product Principles

1. **Clarity over ornament**: Plain operational labels, legible numbers, and clear status hierarchy replace decorative styling.
2. **Low-glare comfort**: Soft, muted light surfaces and restrained contrast reduce eye fatigue without hiding critical anomaly signals.
3. **Honest telemetry**: Display live queue depth, FPS, payload size, and zero/idle states without invented claims or filler.
4. **Decoupled simplicity**: Keep producer (`:5174`) and consumer (`:5173`) responsibilities distinct and linked cleanly across ports.
