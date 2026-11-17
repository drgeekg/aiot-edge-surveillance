# Edge-to-Server Anomaly Detection & Object Alert System

Computer-vision anomaly detection split across a simulated IoT edge node and an
analysis server that communicate strictly over HTTP, paired with two decoupled
React + Vite web consoles, a dual-mode rule engine, asynchronous LangGraph
triage, and signed Hermes/Telegram alerts:

| Entity | Default Port | Role |
|---|---|---|
| **Edge node** (`edge/edge_server.py`, `edge/edge_client.py`) | `:8001` | Owns the video input (webcam, `data/*.mp4` clips, RTSP/HTTP URL, or YouTube URL via `yt-dlp`). Resizes and JPEG-compresses frames and uploads them to the server via `POST /frames`. Exposes `/health`, `/edge/status`, `/edge/config`, and `/edge/frame`. **No detection runs here.** |
| **Analysis server** (`server/app.py`) | `:8000` | Ingest API (`POST /frames`, `POST /events`, REST queries) → bounded queue (drop-oldest, size 8) → `cv-worker` running YOLO26n (ONNX, NMS-free) → `Tracker` → dual-mode `RuleEngine` (Home & Public modes) → SQLite WAL event/anomaly log → async LangGraph text-only triage (`server/agent.py`, fail-open) → console/beep/overlay + HMAC-SHA256 signed Hermes webhook (`server/alerts.py`). |
| **Analytics Console** (`frontend/`, `:5173`) | `:5173` | Overcast Ash & Mineral matte light UI (`ConsoleShell.jsx`) polling `:8000` for the live annotated YOLO feed, KPI strip, person-count timeline, Anomaly Vault, Detection Ledger, and Nodes & Rules view. |
| **Edge Control Deck** (`frontend/`, `:5174`) | `:5174` | Controls the edge node (`:8001`) and mode/arming state (`:8000`): video source selector (`data/*.mp4`, webcam, custom URL), clip rule hints, encoder sliders (FPS, width, JPEG quality, device ID), and synthetic rule injector. |

> **Hardware note:** Raspberry Pi hardware was unavailable. Following faculty
> guidance, the Pi is simulated as an independent OS process (`edge/edge_server.py`
> on `:8001`, or `edge/edge_client.py` CLI) that streams JPEG frames over HTTP to
> the analysis server (`:8000`). The edge node needs only OpenCV, `requests`,
> and FastAPI/Uvicorn (or OpenCV + `requests` for the CLI), so it can move to a
> Raspberry Pi 4 with a USB webcam (V4L2); a CSI Pi Camera would need a
> Picamera2 adapter (not implemented). The system has **not** been tested on Pi
> hardware. GPIO alerting is simulated by console banner, beep, on-frame red
> alert overlay, live UI banner, and optional Telegram delivery via Hermes.

## Quick Start

```bash
pip install -r requirements.txt   # python 3.10-3.12

# 1. get the model (one time)
python scripts/export_model.py    # or Colab: YOLO("yolo26n.pt").export(format="onnx", nms=False)

# 2. start the analysis server (ingest API + CV worker + rules + alerts) - keep ONE worker
uvicorn server.app:app --port 8000          # add --host 0.0.0.0 to accept a second device (requires AIIOT_API_KEY)

# 3. start the simulated IoT edge node (separate terminal)
uvicorn edge.edge_server:app --port 8001    # set AIIOT_SERVER_URL if server is on another host

# 4. start the two React frontends (Overcast Ash & Mineral matte light theme)
cd frontend && npm install
npm run dev:analytics   # http://localhost:5173 — Analytics Console (consumes :8000)
npm run dev:edge        # http://localhost:5174 — Edge Control Deck (controls :8001 & :8000)
```

### Optional CLI Edge Emitter, Simulator & Telegram Gateway

```bash
# CLI edge node alternative (hot-reloads data/edge_state.json)
python edge/edge_client.py --source 0 --server http://localhost:8000                # webcam
python edge/edge_client.py --source data/demo.mp4 --server http://localhost:8000    # video file (loops)
python edge/edge_client.py --source "http://<phone-ip>:8080/video" --server http://localhost:8000   # IP camera

# no-camera fallback: skips the detector and injects scripted detections to POST /events
python scripts/simulator.py

# optional Hermes gateway (:8644) for Telegram alert card delivery (requires HERMES_WEBHOOK_SECRET in .env)
hermes gateway run
```

Config defaults in `config.yaml`: `device_id: edge-01`, `fps: 5`, `width: 960`, `jpeg_quality: 90` (CLI `edge_client.py` accepts `--device-id`, `--fps`, `--width`, `--quality`).
Local sample clips live in `data/*.mp4` (including `sec_cam_1.mp4`–`sec_cam_4.mp4` for Home/Public mode scenarios).

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/diagrams/README.md](docs/diagrams/README.md).
Pipeline: edge capture → resize/JPEG → `POST /frames` (`<= 2 MB`, `<= 4096×4096`) →
bounded queue (8, drop-oldest) → `cv-worker`: YOLO26n ONNX → `Tracker` →
dual-mode `RuleEngine` → SQLite WAL → async LangGraph text-only triage →
`alerts.fire()` (console, beep, overlay, signed Hermes webhook).
`POST /events` (detection injection, used by `scripts/simulator.py` and the Edge Control Deck injector) joins the same lock-serialized `ingest_detections()` path at the rule stage.

## Design Trade-Off
Inference runs on the analysis server, not on the edge node. Streaming frames
costs bandwidth and sends video off the capture device; the edge node reduces
this via resizing, JPEG compression, and FPS throttling, while raw images never
leave the local server to the cloud LLM (LangGraph receives text metadata only).
Because the detector is isolated in `server/detector.py`, moving inference onto
the edge node and posting JSON detections to `POST /events` is a clean next step.

## Why YOLO26n + ONNX
NMS-free end-to-end head gives a `(1, 300, 6)` output with no post-processing;
the nano ONNX export is ~9.8 MB (`yolo26n.onnx`); `onnxruntime` requires no
PyTorch at runtime. Ultralytics reports up to ~43% faster CPU ONNX inference
than YOLO11n; TFLite is the syllabus-themed alternative, while ONNX was chosen
for the NMS-free export and torch-free runtime.

## Measured Performance (`12th Gen Intel(R) Core(TM) i5-12500H`, 640×480 @ 5 FPS)

| Mode | Avg Payload / Frame | Bandwidth (@ 5 FPS) | Avg Inference (`ms`) | Single-Thread Capacity | Avg E2E Latency (`ms`) |
|---|---|---|---|---|---|
| Raw Uncompressed BGR (baseline) | 900.0 KB | 4,500.0 KB/s | — | — | — |
| **Edge → Server JPEG (`POST /frames`, q=70)** | **23.3 – 31.0 KB** | **116.5 – 155.0 KB/s** | **27.6 ms** | **~36.2 FPS** | **50.5 – 67.0 ms** |
| Edge-Inference JSON (`POST /events` seam) | ~0.18 KB | ~0.9 KB/s | — | — | < 5.0 ms |

*(Full-stack live run measurements at 960 px / q=90 and Telegram alert timelines are documented in `report/main.pdf`.)*

## Verification

```bash
# Backend unit & API security tests (26 tests)
pytest tests -q

# Offline precision/recall evaluation on labelled clips
python scripts/eval.py

# Frontend build & Playwright smoke check (with servers running)
cd frontend && npm run build
node scripts/test_frontends.js
```

## Docs, Design & Report
- [docs/PRD.md](docs/PRD.md) — product requirements
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components & data flow
- [docs/API_SPEC.md](docs/API_SPEC.md) — REST contract
- [docs/DATABASE.md](docs/DATABASE.md) — SQLite WAL schema
- [docs/ANOMALY_RULES.md](docs/ANOMALY_RULES.md) — rule definitions
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md) — acceptance criteria & test cases
- [docs/diagrams/README.md](docs/diagrams/README.md) — interactive Archify diagrams
- [PRODUCT.md](PRODUCT.md) & [DESIGN.md](DESIGN.md) — frontend product & Overcast Ash design system spec
- [report/main.pdf](report/main.pdf) ([report/main.tex](report/main.tex)) — IEEE-formatted project report & figures
