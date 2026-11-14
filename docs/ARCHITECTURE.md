# ARCHITECTURE.md

```
 ┌────────────────── EDGE NODE (separate process / device) ──────────────────┐
 │  webcam / mp4 / RTSP or HTTP URL                                          │
 │            │                                                              │
 │   capture.py (VideoSource) → edge_client.py: throttle → resize → JPEG     │
 └──────────────────────────────────┬────────────────────────────────────────┘
                                    │ HTTP  POST /frames
                                    │ (JPEG body + device_id, ts, seq)
                                    ▼
 ┌────────────────────────── SERVER (laptop) ────────────────────────────────┐
 │  server/app.py  FastAPI :8000  (ingest API)                               │
 │            │ enqueue: bounded queue, drop-oldest                          │
 │            ▼                                                              │
 │  server/worker.py  (processing engine, background thread)                 │
 │    decode → detector.py (YOLO26n ONNX) ─┐                                 │
 │                                         ▼                                 │
 │             pipeline.py  ingest_detections()  ◄── POST /events            │
 │               debounce → tracker.py → rules.py      (injected detections) │
 │                  │                      │                                 │
 │                  ▼                      ▼                                 │
 │             db.py (SQLite, WAL)    alerts.py (banner/beep/overlay flag)   │
 │    annotated latest frame (memory) ◄── worker                             │
 │                                                                           │
 │  GET /frames/latest /events /anomalies /stats /health /devices            │
 │            ▲                                                              │
 │  dashboard/app.py  Streamlit :8501 (API only)                             │
 └───────────────────────────────────────────────────────────────────────────┘

  scripts/simulator.py ──HTTP POST /events──► server/app.py   [no-CV fallback]
```

Two separate entities (edge, server) communicate **only** through the HTTP API.
Inside the server, ingest (API) and processing (worker) are separate
components connected by a queue.

## Project layout
```
edge/capture.py        edge/edge_client.py
server/app.py          server/worker.py     server/pipeline.py
server/detector.py     server/tracker.py    server/rules.py
server/db.py           server/alerts.py
dashboard/app.py       scripts/export_model.py   scripts/simulator.py
tests/test_rules.py    config.yaml
```

## Component Contracts

### edge/capture.py
- `class VideoSource(src: str | int)` → `.read() -> frame | None`, `.release()`.
- Source forms: `0` (webcam), `"data/demo.mp4"` (file, auto-loop), `"rtsp://..."` or `"http://.../video"`.

### edge/edge_client.py
- CLI: `--source`, `--server`, `--device-id`, `--fps`, `--width`, `--quality`.
- Loop: read frame → skip if less than `1/fps` since last send → resize
  (keep aspect, width = `--width`) → `cv2.imencode('.jpg', quality)` →
  `POST /frames` (timeout 2 s, one request in flight).
- On error: log, exponential backoff up to 5 s, then continue with a fresh
  frame (stale frames are discarded; real-time semantics).
- Prints every 5 s: frames sent, KB/s, last queue depth reported by server.

### server/app.py
- Endpoints per API_SPEC.md. `POST /frames` validates (JPEG magic bytes, ≤ 2 MB),
  updates the device registry, and enqueues `(device_id, ts, seq, source_kind, jpeg_bytes, received_at)`.
- Queue full → remove oldest, `frames_dropped += 1`, enqueue new.
- Starts the worker thread on startup.

### server/worker.py
- Loop: `get(timeout=1)` → skip if `process_every_n_frames` says so → `cv2.imdecode`
  → `detector.detect()` (time it → `inference_ms`) →
  `ingest_detections(device_id, ts, detections, source)` → draw boxes + labels
  (+ red border while an alert is active) → store JPEG in `latest[device_id]` →
  insert a `frame_metrics` row (`frame_bytes`, `inference_ms`, `e2e_ms`).

### server/pipeline.py
- `ingest_detections(device_id, ts, detections, source) -> list[Anomaly]` is
  the **single entry point** for both ingestion paths (worker and `POST /events`).
- Under one `threading.Lock`: debounce and `insert_event`s → per-device
  `RuleEngine.update()` → `insert_anomaly` + `alerts.fire()` for each result.
- Holds `devices[device_id] = DeviceState(tracker, rule_engine, last_seen, frames_received)`.

### server/detector.py
- `class ONNXRuntimeDetector(model_path: str, conf: float = 0.4)`
- `.detect(frame_bgr) -> list[dict]`, each `{class_name, conf, box: (x1,y1,x2,y2)}`
  with `box` **normalized to 0..1** of the original frame.
- Internals: letterbox to 640×640 (gray 114 pad), BGR→RGB, /255, NCHW float32;
  output `(1,300,6)` rows filtered by `score >= conf`; undo letterbox and
  normalize. No NMS needed.

### server/tracker.py
- Per-device, per-class centroid tracks (greedy match by IoU, then centroid distance).
- A track survives ≤ `track_timeout` (3 s) of absence.
- Each track stores: `first_seen`, `last_seen`, anchor box (position ≈ 5 s ago),
  `last_person_near_ts`.
- Used by **both** R2 (track lifetime) and R3 (unattended dwell).

### server/rules.py
- `class RuleEngine(config)` → `.update(detections, ts) -> list[Anomaly]`
- Implements R1/R2/R3 with per-rule 10 s cooldown; emits
  `Anomaly(rule, detail, severity, ts)`. Pure logic, no I/O (unit-testable).

### server/db.py
- `init_db()` sets `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`.
- `insert_event`, `insert_anomaly`, `insert_frame_metric`, `recent_events(limit, ...)`,
  `recent_anomalies(limit, ...)`, `stats()`. stdlib `sqlite3`, parameterized
  SQL, one connection per thread.

### server/alerts.py
- `fire(anomaly)`: colored console banner + beep + sets `alert_active_until`
  (read by the worker for the red overlay and by `/stats` for the dashboard banner).
- Beep: `winsound.Beep` on Windows, `afplay` on macOS, `\a` fallback elsewhere.
  Test the beep on your own OS before the demo.

### dashboard/app.py
- Reads only the API: `/frames/latest`, `/stats`, `/events`, `/anomalies`.
  Shows annotated frame, recent tables, person-count chart, red banner when an
  anomaly occurred in the last 15 s. Refresh every 2 s.

### scripts/simulator.py
- Phases (0-30 s normal / 30-60 s occupancy + unexpected / 60-90 s dwell);
  POSTs one event per class per second to `http://localhost:8000/events`;
  prints status and a summary at the end.

## Timing & concurrency
- Rules use the edge capture `ts`, so queue delay does not distort dwell.
- `e2e_ms = server finish time - ts`; meaningful only on the same host or
  NTP-synced devices.
- The edge sends one frame at a time, so the server sees at most one in-flight
  frame per device; the queue and drop-oldest policy cover bursts and slow inference.
- `ingest_lock` serializes worker and `POST /events` access to rule state and
  DB writes. Dashboard and API reads use separate connections (WAL).

## config.yaml (keys)
```yaml
edge:   {device_id: edge-01, fps: 5, width: 640, jpeg_quality: 70}
server: {queue_size: 8, conf: 0.4, process_every_n_frames: 1, debounce_seconds: 2}
rules:  # see ANOMALY_RULES.md
```

## Deployment Variants
| Variant | Commands |
|---|---|
| All on one laptop | 3 terminals: `uvicorn server.app:app`, `streamlit run dashboard/app.py`, `python edge/edge_client.py ...` |
| Two devices (LAN) | Server: `uvicorn server.app:app --host 0.0.0.0`; edge on the other device: `--server http://<laptop-ip>:8000` |
| Public demo | `cloudflared tunnel --url http://localhost:8000`; edge uses the printed https URL; close it after the demo |
| Simulator only (no CV) | `uvicorn server.app:app` + `python scripts/simulator.py` + `streamlit run dashboard/app.py` |
| Pi (future) | Run `edge/` on the Pi with a USB webcam (V4L2); CSI camera needs a Picamera2 adapter; server unchanged |
| Edge-inference mode (future) | Move `detector.py` to the edge node; send only JSON to `POST /events` |
