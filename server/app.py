from contextlib import asynccontextmanager
import os
import queue
import struct
import threading
import time
from typing import Dict, Literal, Optional, Tuple
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from server import db, pipeline
from edge import controller as edge_controller

MAX_FRAME_BYTES = 2 * 1024 * 1024
MAX_JPEG_DIM = 4096
ALLOWED_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
]


def _get_jpeg_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """Extract (width, height) from JPEG SOF marker without full pixel decompression."""
    n = len(data)
    if n < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    sof_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7) or marker == 0x01:
            continue
        if marker == 0xDA:  # Start of Scan
            break
        if i + 2 > n:
            break
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2 or i + seg_len > n:
            break
        if marker in sof_markers and seg_len >= 7:
            h, w = struct.unpack(">HH", data[i + 3 : i + 7])
            return (w, h)
        i += seg_len
    return None


def verify_api_key(request: Request = None) -> None:
    """Enforce X-API-Key authentication whenever AIIOT_API_KEY is set or bound remotely."""
    expected_key = os.getenv("AIIOT_API_KEY", "").strip()
    server_host = None
    client_host = None
    provided_key = ""
    if request is not None:
        provided_key = (request.headers.get("x-api-key") or "").strip()
        if request.scope.get("server"):
            server_host = request.scope["server"][0]
        if request.client:
            client_host = request.client.host

    local_hosts = {"127.0.0.1", "::1", "localhost", "testclient", None}
    bound_all_interfaces = (
        server_host == "0.0.0.0"
        or os.getenv("AIIOT_HOST") == "0.0.0.0"
        or (client_host not in local_hosts)
    )

    if expected_key:
        if not provided_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key")
        if provided_key != expected_key:
            raise HTTPException(status_code=403, detail="Invalid X-API-Key")
    elif bound_all_interfaces:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key (env AIIOT_API_KEY) is required when bound to 0.0.0.0 or remote interface",
        )

_cfg = pipeline.load_config()
QUEUE_SIZE = int(_cfg.get("server", {}).get("queue_size", 8))

frame_queue: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)
queue_lock = threading.Lock()
frames_received_total: int = 0
frames_dropped_total: int = 0
latest_frames: Dict[str, bytes] = {}
latest_frame_device: Optional[str] = None
START_TIME = time.time()


class DetectionEvent(BaseModel):
    """Pydantic request schema for POST /events synthetic or edge-inferred detections."""

    ts: float
    source: str = "api"
    device_id: str = "sim-01"
    object_class: str
    count: int = 1
    avg_conf: float = 1.0
    box: Optional[Tuple[float, float, float, float]] = None


class AnomalyEvent(BaseModel):
    """Pydantic schema representing an emitted security/safety anomaly alert."""

    ts: float
    device_id: str
    rule: str
    detail: str
    severity: Literal["info", "warning", "critical"]


def install_proactor_silence_handler() -> None:
    """Suppress harmless Windows Proactor WinError 10054 when browsers close polled sockets."""
    import asyncio

    loop = asyncio.get_running_loop()
    orig = loop.get_exception_handler()

    def _handler(lp, ctx):
        exc = ctx.get("exception")
        if isinstance(exc, ConnectionResetError) and getattr(exc, "winerror", None) == 10054:
            return
        if orig:
            orig(lp, ctx)
        else:
            lp.default_exception_handler(ctx)

    loop.set_exception_handler(_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage SQLite initialization, CV worker startup, optional embedded edge, and shutdown."""
    install_proactor_silence_handler()
    db.init_db()
    try:
        from server import worker
        worker.start_worker()
    except ImportError:
        pass
    if os.getenv("EMBEDDED_EDGE") == "1":
        edge_controller.controller.start()
    try:
        yield
    finally:
        edge_controller.controller.stop()
        try:
            from server import worker
            worker.stop_worker()
        except ImportError:
            pass


app = FastAPI(title="Edge-to-Server Anomaly Detection API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/frames", status_code=202, dependencies=[Depends(verify_api_key)])
async def post_frames(
    request: Request,
    device_id: str = Query("edge-01"),
    ts: Optional[float] = Query(None),
    seq: int = Query(0),
    source_kind: str = Query("live"),
):
    """Validate JPEG bounds and enqueue raw frames with drop-oldest backpressure."""
    global frames_received_total, frames_dropped_total
    # Re-verify explicitly so unit tests calling post_frames() directly exercise auth
    verify_api_key(request)

    # Reject declared oversized payloads before reading request body into memory
    cl_header = request.headers.get("content-length")
    if cl_header is not None:
        try:
            if int(cl_header) > MAX_FRAME_BYTES:
                raise HTTPException(status_code=413, detail="Content-Length exceeds 2 MB limit")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header")

    body = await request.body()
    if len(body) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="Frame exceeds 2 MB limit")
    if len(body) < 4 or body[:2] != b"\xff\xd8":
        raise HTTPException(status_code=400, detail="Invalid JPEG payload")

    dims = _get_jpeg_dimensions(body)
    if dims is not None:
        w, h = dims
        if w <= 0 or h <= 0 or w > MAX_JPEG_DIM or h > MAX_JPEG_DIM:
            raise HTTPException(
                status_code=400,
                detail=f"JPEG dimensions {w}x{h} exceed maximum allowed {MAX_JPEG_DIM}x{MAX_JPEG_DIM}",
            )

    capture_ts = float(ts) if ts is not None else time.time()
    received_at = time.time()
    pipeline.register_frame_received(device_id, capture_ts, source_kind)

    dropped_oldest = False
    with queue_lock:
        frames_received_total += 1
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
                frames_dropped_total += 1
                dropped_oldest = True
            except queue.Empty:
                pass
        frame_queue.put_nowait((device_id, capture_ts, seq, source_kind, body, received_at))
        q_depth = frame_queue.qsize()

    return {
        "status": "queued",
        "queue_depth": q_depth,
        "dropped_oldest": dropped_oldest,
    }


@app.post("/events", dependencies=[Depends(verify_api_key)])
def post_events(ev: DetectionEvent, request: Request = None):
    """Ingest a structured DetectionEvent synchronously through the shared rule pipeline."""
    verify_api_key(request)
    det = {
        "class_name": ev.object_class,
        "count": ev.count,
        "avg_conf": ev.avg_conf,
        "box": ev.box,
    }
    fired = pipeline.ingest_detections(
        device_id=ev.device_id,
        ts=ev.ts,
        detections=[det],
        source=ev.source,
    )
    out_anomalies = [
        {
            "ts": a.ts,
            "device_id": ev.device_id,
            "rule": a.rule,
            "detail": a.detail,
            "severity": a.severity,
        }
        for a in fired
    ]
    return {"status": "logged", "anomalies": out_anomalies}


@app.get("/events")
def get_events(
    limit: int = Query(100, ge=1, le=1000),
    object_class: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
):
    """Return newest-first debounced detection events filtered optionally by class or device."""
    return db.recent_events(limit=limit, object_class=object_class, device_id=device_id)


@app.get("/anomalies")
def get_anomalies(
    limit: int = Query(100, ge=1, le=1000),
    device_id: Optional[str] = Query(None),
):
    """Return newest-first anomaly alerts from SQLite, optionally filtered by device_id."""
    return db.recent_anomalies(limit=limit, device_id=device_id)


@app.get("/frames/latest")
def get_latest_frame(device_id: Optional[str] = Query(None)):
    """Serve the latest annotated JPEG frame for device_id or the most recent active device."""
    target = device_id or latest_frame_device
    if not target or target not in latest_frames:
        if latest_frames and not device_id:
            target = next(iter(latest_frames.keys()))
        else:
            raise HTTPException(status_code=404, detail="No frame available yet")
    return Response(content=latest_frames[target], media_type="image/jpeg")


@app.get("/devices")
def get_devices():
    """Return all registered edge/API devices with last-seen timestamp and frame counts."""
    with pipeline.ingest_lock:
        return [
            {
                "device_id": st.device_id,
                "last_seen_ts": st.last_seen,
                "frames_received": st.frames_received,
                "source_kind": st.source_kind,
            }
            for st in pipeline.devices.values()
        ]


@app.get("/stats")
def get_stats():
    """Combine SQLite event/latency aggregates with live server queue and frame counters."""
    s = db.stats()
    with queue_lock:
        q_depth = frame_queue.qsize()
        f_recv = frames_received_total
        f_drop = frames_dropped_total
    return {
        "total_events": s["total_events"],
        "anomalies_by_rule": s["anomalies_by_rule"],
        "uptime_s": round(time.time() - START_TIME, 2),
        "fps": s["fps"],
        "queue_depth": q_depth,
        "frames_received": f_recv,
        "frames_dropped": f_drop,
        "avg_frame_kb": s["avg_frame_kb"],
        "avg_inference_ms": s["avg_inference_ms"],
        "avg_e2e_ms": s["avg_e2e_ms"],
        "last_anomaly_ts": s["last_anomaly_ts"],
    }


@app.get("/health")
def get_health():
    """Verify worker liveness and ONNX model presence, returning 503 if degraded."""
    worker_status = "stopped"
    try:
        from server import worker
        worker_status = "running" if worker.is_running() else "stopped"
    except ImportError:
        pass
    model_path = "yolo26n.onnx"
    if worker_status != "running" or not os.path.exists(model_path):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "model": model_path,
                "model_exists": os.path.exists(model_path),
                "db": db.DB_PATH,
                "worker": worker_status,
            },
        )
    return {
        "status": "ok",
        "model": model_path,
        "db": db.DB_PATH,
        "worker": worker_status,
        "rules": _cfg.get("rules", {}),
    }


class EdgeConfigUpdate(BaseModel):
    """Pydantic request schema for live embedded-edge configuration updates."""

    source: Optional[str] = None
    device_id: Optional[str] = None
    fps: Optional[float] = Field(None, ge=0.5, le=30.0)
    width: Optional[int] = Field(None, ge=160, le=1920)
    quality: Optional[int] = Field(None, ge=10, le=100)
    streaming: Optional[bool] = None

    @field_validator("source")
    @classmethod
    def check_allowed_source(cls, v: Optional[str]) -> Optional[str]:
        """Validate source paths and URL schemes against traversal/disallowed schemes."""
        if v is None:
            return None
        return edge_controller.validate_source(v)


@app.get("/edge/status")
def get_edge_status():
    """Return current embedded edge emitter configuration, uplink rate, and sources."""
    return edge_controller.controller.get_status()


@app.post("/edge/config", dependencies=[Depends(verify_api_key)])
def post_edge_config(payload: EdgeConfigUpdate, request: Request = None):
    """Apply validated runtime updates to the embedded edge emitter controller."""
    verify_api_key(request)
    try:
        return edge_controller.controller.update_config(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/edge/frame")
def get_edge_frame():
    """Serve the most recent raw pre-inference JPEG captured by the embedded edge emitter."""
    jpeg = edge_controller.controller.latest_jpeg
    if not jpeg:
        raise HTTPException(status_code=404, detail="No edge frame captured yet")
    return Response(content=jpeg, media_type="image/jpeg")


class ModeUpdate(BaseModel):
    """Pydantic request schema for switching deployment mode and home arming state."""

    mode: Literal["home", "public"]
    arming: Optional[Literal["disarmed", "armed_home", "armed_night", "armed_away"]] = None


@app.get("/mode")
def get_mode():
    """Return the active deployment mode ('home' or 'public') and arming level."""
    return pipeline.get_active_mode()


@app.post("/mode", dependencies=[Depends(verify_api_key)])
def post_mode(payload: ModeUpdate, request: Request = None):
    """Switch active deployment mode/arming across the pipeline and live RuleEngines."""
    verify_api_key(request)
    try:
        return pipeline.set_active_mode(payload.mode, payload.arming)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
