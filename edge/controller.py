import json
import os
import threading
import time
import cv2
import requests
import yaml
from edge.capture import VideoSource

STATE_PATH = os.path.join("data", "edge_state.json")


def load_defaults() -> dict:
    """Load default edge streaming parameters from config.yaml and detect default video clip."""
    cfg = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            cfg = (yaml.safe_load(f) or {}).get("edge", {})
    default_src = "data/demo.mp4" if os.path.exists("data/demo.mp4") else "0"
    return {
        "source": default_src,
        "device_id": cfg.get("device_id", "edge-01"),
        "fps": float(cfg.get("fps", 5.0)),
        "width": int(cfg.get("width", 640)),
        "quality": int(cfg.get("jpeg_quality", 70)),
        "streaming": True,
    }


def validate_source(src: str) -> str:
    """Validate that source is a camera index, allowlisted URL scheme, or safe data/*.mp4 path."""
    s = str(src).strip()
    if not s:
        raise ValueError("Source cannot be empty")
    if s.isdigit():
        return s
    if s.startswith(("http://", "https://", "rtsp://")):
        return s
    # Must be a .mp4 inside data/ with no traversal outside data/
    data_root = os.path.abspath("data")
    cand = os.path.abspath(s)
    if (
        os.path.commonpath([data_root, cand]) == data_root
        and os.path.dirname(cand) == data_root
        and cand.lower().endswith(".mp4")
    ):
        return s
    raise ValueError(
        "Disallowed source: must be a camera index, data/*.mp4, or allowlisted URL scheme (http/https/rtsp)"
    )


def save_state_file(state: dict) -> None:
    """Atomically persist edge runtime config to data/edge_state.json via temp file swap."""
    os.makedirs("data", exist_ok=True)
    tmp_path = f"{STATE_PATH}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_PATH)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


class EdgeEmitterController:
    """Thread-safe controller managing embedded video capture, JPEG encoding, and /frames upload."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        """Initialize configuration state, lock, and rolling telemetry counters."""
        self.server_url = server_url.rstrip("/")
        self.lock = threading.Lock()
        self.cfg = load_defaults()
        save_state_file(self.cfg)
        self.latest_jpeg: bytes | None = None
        self.frames_sent = 0
        self.window_fps = 0.0
        self.window_kbps = 0.0
        self.last_frame_kb = 0.0
        self.server_queue_depth = 0
        self.source_kind = "file"
        self.status_msg = "Initializing..."
        self.error_msg: str | None = None
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background edge streaming daemon thread if not already active."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the edge worker thread to stop and join up to timeout seconds."""
        self._stop = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    def update_config(self, updates: dict) -> dict:
        """Validate and apply runtime config updates, persist edge_state.json, and return status."""
        if "source" in updates and updates["source"] is not None:
            updates["source"] = validate_source(str(updates["source"]))
        with self.lock:
            for k in ("source", "device_id", "fps", "width", "quality", "streaming"):
                if k in updates and updates[k] is not None:
                    self.cfg[k] = updates[k]
            save_state_file(self.cfg)
        return self.get_status()

    def list_sources(self) -> list[dict]:
        """Return curated presets plus any local .mp4 clips discovered inside data/."""
        items = [
            {
                "id": "data/demo.mp4",
                "label": "Unattended Bag Scenario (data/demo.mp4)",
                "tag": "Triggers R2 & R3",
                "kind": "file",
            },
            {
                "id": "data/demo_attended.mp4",
                "label": "Attended Bag & Crowd Scenario (data/demo_attended.mp4)",
                "tag": "Triggers R1 · Resets R3",
                "kind": "file",
            },
            {
                "id": "0",
                "label": "Integrated / USB Webcam (Index 0)",
                "tag": "Live Camera",
                "kind": "live",
            },
        ]
        known = {x["id"] for x in items}
        extra_meta = {
            "data/people-detection.mp4": ("People Crowd Detection (people-detection.mp4)", "Public · Crowd/Loiter"),
            "data/person-bicycle-car.mp4": ("Street: Person, Bike & Car (person-bicycle-car.mp4)", "Zones & Vehicles"),
            "data/worker-zone.mp4": ("Zone Intrusion Demo (worker-zone.mp4)", "Home/Public Zones"),
            "data/store-aisle.mp4": ("Indoor Aisle / Queue (store-aisle.mp4)", "Queue & Dwell"),
            "data/car-detection.mp4": ("Vehicle / Driveway Monitoring (car-detection.mp4)", "Driveway / No-Park"),
            "data/sec_cam_1.mp4": ("Security Cam 1 · 1080p Person & Car (sec_cam_1.mp4)", "Home Driveway · 48s"),
            "data/sec_cam_2.mp4": ("Security Cam 2 · Continuous Indoor/Porch (sec_cam_2.mp4)", "Long Feed · 131s"),
            "data/sec_cam_3.mp4": ("Security Cam 3 · Continuous Street/Driveway (sec_cam_3.mp4)", "Long Feed · 132s"),
            "data/sec_cam_4.mp4": ("Security Cam 4 · Person Entry Clip (sec_cam_4.mp4)", "Entry · 15s"),
        }
        if os.path.exists("data"):
            for fn in sorted(os.listdir("data")):
                if fn.lower().endswith(".mp4"):
                    rel = f"data/{fn}"
                    if rel not in known:
                        lbl, tag = extra_meta.get(rel, (f"Video Clip ({rel})", "Local MP4"))
                        items.append(
                            {
                                "id": rel,
                                "label": lbl,
                                "tag": tag,
                                "kind": "file",
                            }
                        )
        return items

    def get_status(self) -> dict:
        """Return a thread-safe snapshot of active config, uplink telemetry, and sources."""
        with self.lock:
            return {
                **self.cfg,
                "frames_sent": self.frames_sent,
                "window_fps": round(self.window_fps, 1),
                "window_kbps": round(self.window_kbps, 1),
                "last_frame_kb": round(self.last_frame_kb, 1),
                "server_queue_depth": self.server_queue_depth,
                "source_kind": self.source_kind,
                "status_msg": self.status_msg,
                "error_msg": self.error_msg,
                "available_sources": self.list_sources(),
            }

    def _run_loop(self) -> None:
        """Background loop that hot-swaps VideoSource, resizes/JPEG-encodes frames, and POSTs to /frames."""
        vs: VideoSource | None = None
        active_src: str | None = None
        session = requests.Session()
        last_send = 0.0
        win_start = time.time()
        win_sent = 0
        win_bytes = 0

        while not self._stop:
            with self.lock:
                cfg = dict(self.cfg)

            if not cfg.get("streaming", True):
                with self.lock:
                    self.status_msg = "Paused"
                    self.window_fps = 0.0
                    self.window_kbps = 0.0
                time.sleep(0.15)
                continue

            target_src = str(cfg["source"])
            if vs is None or target_src != active_src:
                if vs is not None:
                    vs.release()
                    vs = None
                try:
                    vs = VideoSource(target_src)
                    active_src = target_src
                    with self.lock:
                        self.source_kind = vs.source_kind
                        self.error_msg = None
                        self.status_msg = f"Streaming ({vs.source_kind})"
                except Exception as e:
                    with self.lock:
                        self.error_msg = str(e)
                        self.status_msg = "Source Error"
                    time.sleep(1.0)
                    continue

            interval = 1.0 / max(0.5, float(cfg["fps"]))
            now = time.time()
            if (now - last_send) < interval:
                time.sleep(max(0.005, min(0.04, interval - (now - last_send))))
                continue

            frame = vs.read()
            if frame is None:
                time.sleep(0.05)
                continue

            h, w = frame.shape[:2]
            target_w = int(cfg["width"])
            if w != target_w and w > 0:
                new_h = max(1, int(round(h * (target_w / float(w)))))
                frame = cv2.resize(frame, (target_w, new_h), interpolation=cv2.INTER_AREA)

            ok, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(cfg["quality"])])
            if not ok:
                continue
            jpeg_bytes = enc.tobytes()
            capture_ts = time.time()
            last_send = capture_ts

            with self.lock:
                self.latest_jpeg = jpeg_bytes
                self.last_frame_kb = len(jpeg_bytes) / 1024.0
                seq = self.frames_sent + 1

            try:
                api_key = os.getenv("AIIOT_API_KEY", "").strip()
                hdrs = {"Content-Type": "image/jpeg"}
                if api_key:
                    hdrs["X-API-Key"] = api_key
                resp = session.post(
                    f"{self.server_url}/frames",
                    params={
                        "device_id": cfg["device_id"],
                        "ts": f"{capture_ts:.4f}",
                        "seq": seq,
                        "source_kind": vs.source_kind,
                    },
                    data=jpeg_bytes,
                    headers=hdrs,
                    timeout=2.0,
                )
                resp.raise_for_status()
                q_depth = resp.json().get("queue_depth", 0)
                win_sent += 1
                win_bytes += len(jpeg_bytes)
                elapsed = max(0.001, time.time() - win_start)
                with self.lock:
                    self.frames_sent = seq
                    self.server_queue_depth = q_depth
                    self.window_fps = win_sent / elapsed
                    self.window_kbps = (win_bytes / 1024.0) / elapsed
                    self.status_msg = f"Emitting → POST /frames ({vs.source_kind})"
                    self.error_msg = None
                if elapsed >= 4.0:
                    win_start = time.time()
                    win_sent = 0
                    win_bytes = 0
            except Exception as e:
                with self.lock:
                    self.status_msg = "Awaiting Server..."
                    self.error_msg = f"POST /frames error: {e}"
                time.sleep(0.6)


controller = EdgeEmitterController()
