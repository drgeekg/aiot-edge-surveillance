# API_SPEC.md - FastAPI service (port 8000)

## Conventions
- JSON everywhere except frame upload (raw JPEG) and `/frames/latest` (JPEG).
- Timestamps are epoch seconds (float); `ts` on frames is the **edge capture time**.
- Box coordinates are normalized 0..1: `(x1, y1, x2, y2)`.
- Errors: `400` validation, `404` not found, `413` frame too large, `500` with `{"detail": "..."}`.
- Two ingestion paths, one pipeline: the worker (from `/frames`) and `POST /events`
  both call `ingest_detections()`.

## Schemas (Pydantic)

```python
class DetectionEvent(BaseModel):
    ts: float                          # epoch seconds
    source: str = "api"                # 'live' | 'file' | 'url' | 'api'
    device_id: str = "sim-01"
    object_class: str                  # COCO class name
    count: int = 1
    avg_conf: float = 1.0
    box: Optional[Tuple[float, float, float, float]] = None   # normalized; needed for R3 on injected events

class AnomalyEvent(BaseModel):
    ts: float
    device_id: str
    rule: str                          # 'occupancy_spike' | 'unexpected_object' | 'object_dwell'
    detail: str
    severity: Literal['info', 'warning', 'critical']
```

## Endpoints

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| POST | `/frames?device_id=&ts=&seq=&source_kind=` | body: raw JPEG (`Content-Type: image/jpeg`, ≤ 2 MB) | `202 {"status":"queued","queue_depth":int,"dropped_oldest":bool}` | Edge node uploads one frame; processed asynchronously by the worker |
| POST | `/events` | `DetectionEvent` | `{"status":"logged","anomalies":[AnomalyEvent,...]}` | Detection injection (spoofed-data mode); skips the detector, runs rules immediately |
| GET | `/events?limit=100&object_class=&device_id=` | `limit<=1000` | `list[DetectionEvent]` (+id), newest first | Recent detections |
| GET | `/anomalies?limit=100&device_id=` | query | `list[AnomalyEvent]` (+id), newest first | Recent anomalies |
| GET | `/frames/latest?device_id=` | query | `image/jpeg` (annotated), `404` if none yet | Latest annotated frame for the dashboard |
| GET | `/devices` | - | `[{"device_id":str,"last_seen_ts":float,"frames_received":int,"source_kind":str}]` | Known edge devices |
| GET | `/stats` | - | see below | Counters for dashboard and report |
| GET | `/health` | - | `{"status":"ok","model":"yolo26n.onnx","db":"events.db","worker":"running"}` | Liveness |
| GET | `/docs` | - | Swagger UI (auto) | Demo/screenshot |

### `/stats` response
```json
{
  "total_events": 0,
  "anomalies_by_rule": {"occupancy_spike": 0, "unexpected_object": 0, "object_dwell": 0},
  "uptime_s": 0.0,
  "fps": null,
  "queue_depth": 0,
  "frames_received": 0,
  "frames_dropped": 0,
  "avg_frame_kb": null,
  "avg_inference_ms": null,
  "avg_e2e_ms": null,
  "last_anomaly_ts": null
}
```
`fps` = processed frames per second over the last 10 s (null when idle).
Averages come from `frame_metrics`, last 60 s.

## Examples

```bash
# upload one frame (what edge_client.py does every 200 ms)
curl -X POST "localhost:8000/frames?device_id=edge-01&ts=1762512000.0&seq=1&source_kind=file" \
  -H "Content-Type: image/jpeg" --data-binary @frame.jpg
# → 202 {"status":"queued","queue_depth":1,"dropped_oldest":false}

# inject a detection (spoofed-data mode)
curl -X POST localhost:8000/events -H "Content-Type: application/json" \
  -d '{"ts": 1762512000.0, "object_class": "person", "count": 6, "avg_conf": 0.81}'
# → {"status":"logged","anomalies":[{"ts":...,"device_id":"sim-01","rule":"occupancy_spike",
#     "detail":"6 persons detected (>3)","severity":"warning"}]}
```

## Simulator Drive (demo mode with no camera and no detector)
`python scripts/simulator.py` posts a scripted 90 s scenario, one event per
class per second, `ts = time.time()`:
- 0-30 s: 1-2 persons, allowed objects (normal)
- 30-60 s: person count 6 (R1 fires); `backpack` with a fixed box appears (R2 fires after 5 s)
- 60-90 s: `suitcase` with fixed box `(0.40, 0.55, 0.55, 0.85)` stays, no person boxes near it (R3 fires at 30 s)

## Edge-inference seam
`POST /events` is the same call an edge node would make if the detector ran
on-device. Moving `detector.py` to the edge node requires no server change.
