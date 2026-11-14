# Edge-to-Server Anomaly Detection & Object Alert System

Computer-vision anomaly detection split into two separate entities that talk
over HTTP:

| Entity | Role |
|---|---|
| **Edge node** (`edge/`) | Owns the video input (webcam, video file, or IP-camera URL). Resizes and JPEG-compresses frames and streams them to the server. **No detection runs here.** |
| **Server** (`server/`, the laptop) | Ingest API → processing engine: YOLO26n (ONNX, NMS-free) → tracker → rule engine (occupancy spike / unattended object / object dwell) → SQLite event log → alerts. Also serves the REST API and the Streamlit dashboard. |

> **Hardware note:** Raspberry Pi hardware was unavailable. Following faculty
> guidance, the Pi is simulated: the edge node runs as a standalone process (on
> the same laptop or on a second device) and streams frames over HTTP to the
> laptop, which acts as the server and performs all processing. The edge node
> needs only OpenCV and `requests`, so it can move to a Raspberry Pi 4 with a
> USB webcam (V4L2); the CSI Pi Camera would need a Picamera2 adapter (not
> implemented). The system has **not** been tested on Pi hardware. GPIO
> alerting is simulated by console banner, beep, on-frame red overlay and a
> dashboard banner.

## Quick Start

```bash
pip install -r requirements.txt   # python 3.10-3.12

# 1. get the model (one time)
python scripts/export_model.py    # or Colab: YOLO("yolo26n.pt").export(format="onnx", nms=False)

# 2. start the server (ingest API + processing engine) - keep ONE worker
uvicorn server.app:app --port 8000          # add --host 0.0.0.0 to accept a second device

# 3. start the two React frontends (Coffee-Glass iOS Dark Theme)
cd frontend && npm install
npm run dev:analytics   # http://localhost:5173 — Server Analytics Console (analyzes pipeline)
npm run dev:edge        # http://localhost:5174 — Edge Emitter Control Deck (switches video source & streams to pipeline)

# 4. start the edge node (separate terminal or separate device)
python edge/edge_client.py --source 0 --server http://localhost:8000                # webcam
python edge/edge_client.py --source data/demo.mp4 --server http://localhost:8000    # video file (loops)
python edge/edge_client.py --source "http://<phone-ip>:8080/video" --server http://localhost:8000   # IP camera

# 5. no-camera fallback: skips the detector and injects scripted detections
python scripts/simulator.py
```

Edge options: `--device-id edge-01`, `--fps 5`, `--width 640`, `--quality 70`.

Sample footage: record your own clip or use free stock footage. Downloading
from YouTube is against YouTube's terms.

## Architecture
See ARCHITECTURE.md. Pipeline: edge capture → resize/JPEG → `POST /frames` →
bounded queue → worker: YOLO26n ONNX → tracker → rules → SQLite + alerts.
`POST /events` (detection injection, used by the simulator) joins the same
`ingest_detections()` path at the rule stage.

## Design trade-off (state this in the report)
Inference runs on the server, not on the edge node. Streaming frames costs
bandwidth (measured in the report as KB/s per stream) and sends video off the
capture device. The edge node reduces this by resizing, JPEG compression and
frame-rate throttling. The detector is a self-contained module, so moving it
onto the edge node and sending only JSON to `POST /events` is a documented next
step ("edge-inference mode").

## Why YOLO26n + ONNX
NMS-free end-to-end head gives a `(1,300,6)` output with no post-processing;
the nano ONNX export is ~9.8 MB; onnxruntime needs no PyTorch at runtime.
Ultralytics reports up to ~43% faster CPU ONNX inference than YOLO11n; our own
measurements are in the report (fill in CPU model + FPS). TFLite is the
syllabus-themed alternative; ONNX was chosen for the NMS-free export and
torch-free runtime.

## Measured Performance (`12th Gen Intel(R) Core(TM) i5-12500H`, 640×480 @ 5 FPS)

| Mode | Avg Payload / Frame | Bandwidth (@ 5 FPS) | Avg Inference (`ms`) | Single-Thread Capacity | Avg E2E Latency (`ms`) |
|---|---|---|---|---|---|
| Raw Uncompressed BGR (baseline) | 900.0 KB | 4,500.0 KB/s | — | — | — |
| **Edge → Server JPEG (`POST /frames`, q=70)** | **23.3 – 31.0 KB** | **116.5 – 155.0 KB/s** | **27.6 ms** | **~36.2 FPS** | **50.5 – 67.0 ms** |
| Edge-Inference JSON (`POST /events` seam) | ~0.18 KB | ~0.9 KB/s | — | — | < 5.0 ms |

## Docs
- `docs/PRD.md` - product requirements
- `docs/ARCHITECTURE.md` - components & data flow
- `docs/API_SPEC.md` - REST contract
- `docs/DATABASE.md` - schema
- `docs/ANOMALY_RULES.md` - R1/R2/R3 definitions
- `docs/TEST_PLAN.md` - acceptance criteria & test cases
