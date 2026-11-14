import logging
import os
import queue
import threading
import time
from typing import Optional
import cv2
import numpy as np

from server import alerts, app as server_app, db, pipeline
from server.detector import ONNXRuntimeDetector

logger = logging.getLogger(__name__)

_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_detector: Optional[ONNXRuntimeDetector] = None
_cfg = pipeline.load_config()
_watch_classes = set(_cfg.get("rules", {}).get("watch_classes", ["backpack", "handbag", "suitcase"]))


def _get_detector() -> Optional[ONNXRuntimeDetector]:
    """Lazily load and cache the singleton CPU ONNX detector if yolo26n.onnx exists."""
    global _detector
    # Worker passes conf_stay (lower hysteresis bound) so Tracker handles enter/stay filtering
    if _detector is None and os.path.exists("yolo26n.onnx"):
        srv_cfg = _cfg.get("server", {})
        conf_stay = float(srv_cfg.get("conf_stay", 0.30))
        cls_thresh = srv_cfg.get("class_thresholds", {})
        _detector = ONNXRuntimeDetector("yolo26n.onnx", conf=conf_stay, class_thresholds=cls_thresh)
    return _detector


def _annotate_frame(frame: np.ndarray, detections: list, alert_active: bool) -> bytes:
    """Draw detection bounding boxes and active-alert border overlay, returning JPEG bytes."""
    out = frame.copy()
    h, w = out.shape[:2]
    for d in detections:
        box = d.get("box")
        if not box:
            continue
        x1, y1 = int(box[0] * w), int(box[1] * h)
        x2, y2 = int(box[2] * w), int(box[3] * h)
        cls_name = d.get("class_name", "obj")
        conf = d.get("conf", 1.0)
        color = (0, 165, 255) if cls_name in _watch_classes else (0, 255, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name} {conf:.2f}"
        cv2.putText(
            out,
            label,
            (x1, max(15, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    if alert_active:
        cv2.rectangle(out, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)
        cv2.putText(
            out,
            "ALERT ACTIVE",
            (16, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3,
        )

    ok, buf = cv2.imencode(".jpg", out, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else b""


def _worker_loop() -> None:
    """Consume JPEGs from frame_queue, run ONNX detection + rule pipeline, and record metrics."""
    db.init_db()
    frame_counter = 0
    while not _stop_event.is_set():
        try:
            item = server_app.frame_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        try:
            device_id, capture_ts, seq, source_kind, jpeg_bytes, received_at = item
            frame_counter += 1
            every_n = max(1, int(_cfg.get("server", {}).get("process_every_n_frames", 1)))
            if frame_counter % every_n != 0:
                continue

            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            fh, fw = frame.shape[:2]
            if fh > 4096 or fw > 4096:
                continue

            det_engine = _get_detector()
            t0 = time.perf_counter()
            detections = det_engine.detect(frame) if det_engine is not None else []
            inference_ms = (time.perf_counter() - t0) * 1000.0

            pipeline.ingest_detections(
                device_id=device_id,
                ts=capture_ts,
                detections=detections,
                source=source_kind,
                frame_bgr=frame,
            )

            annotated = _annotate_frame(frame, detections, alerts.is_alert_active())
            if annotated:
                server_app.latest_frames[device_id] = annotated
                server_app.latest_frame_device = device_id

            e2e_ms = max(0.0, (time.time() - capture_ts) * 1000.0)
            db.insert_frame_metric(
                ts=capture_ts,
                device_id=device_id,
                frame_bytes=len(jpeg_bytes),
                inference_ms=round(inference_ms, 2),
                e2e_ms=round(e2e_ms, 2),
            )
        except Exception as exc:
            logger.exception("Worker loop error processing frame: %s", exc)


def start_worker() -> None:
    """Start the background cv-worker daemon thread if not already running."""
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="cv-worker")
    _worker_thread.start()


def stop_worker(timeout: float = 2.0) -> None:
    """Signal the cv-worker thread to stop and wait up to timeout seconds for exit."""
    global _worker_thread
    _stop_event.set()
    if _worker_thread is not None and _worker_thread.is_alive():
        _worker_thread.join(timeout=timeout)
    _worker_thread = None


def is_running() -> bool:
    """Return True while the cv-worker thread is alive."""
    return _worker_thread is not None and _worker_thread.is_alive()
