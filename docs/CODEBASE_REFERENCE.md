# Codebase Reference: Edge-to-Server Anomaly Detection & Alert System

> **Documentation status:** Inline docstrings and JSDoc comments were added across **154 / 154** Python classes/functions and all React/Playwright components & handlers without commenting out or altering any existing executable code (`25/25` pytest tests & Vite production build verified).

---

## Navigation & Companion Artifacts

| Artifact | Purpose | Link |
| --- | --- | --- |
| **Interactive File & Function Explorer** | Searchable, sidebar-navigable HTML documentation | [`docs/CODEBASE_REFERENCE.html`](CODEBASE_REFERENCE.html) |
| **Archify System Explainer** | Validated architecture & dual-ingest walkthrough | [`docs/diagrams/codebase-overview.html`](diagrams/codebase-overview.html) |
| **Graphify Knowledge Graph** | Force-directed call, import & community graph | [`graphify-out/graph.html`](../graphify-out/graph.html) |
| **Graphify Audit Report** | God nodes, structural communities & connections | [`graphify-out/GRAPH_REPORT.md`](../graphify-out/GRAPH_REPORT.md) |
| **Native Archify Diagrams (12)** | ERD, sequence, lifecycle, waterfall & security | [`docs/diagrams/README.md`](diagrams/README.md) |

---

## High-Level Architecture Summary

1. **Edge Node (`edge/`):** Captures BGR frames from webcam, local MP4, YouTube (`yt-dlp`), or RTSP/HTTP URLs, resizes and JPEG-compresses them, and streams `POST /frames` over HTTP. **Zero ML inference runs on the edge.**
2. **Backend Server (`server/`):** Single-process FastAPI server (`:8000`) with a bounded drop-oldest queue (`maxsize=8`), a daemon CV worker (`cv-worker`) running CPU `ONNXRuntimeDetector` (`yolo26n.onnx`), a unified `ingest_detections()` pipeline (`POST /frames` + `POST /events`), IoU/centroid `Tracker`, multi-mode `RuleEngine` (`public` and `home`), SQLite WAL storage (`events.db`), local/HMAC webhook alerting (`alerts.py`), and optional fail-open LangGraph triage (`agent.py`).
3. **Frontend (`frontend/`):** Single React + Vite codebase serving **Server Analytics Console** (`:5173`) and **Edge Emitter Control Deck** (`:5174`) via runtime port/query/env multiplexing in `main.jsx`.

---

## 1. Backend (`server/`)

### 1.1 [`server/app.py`](../server/app.py) (408 LOC)
- **Role:** FastAPI HTTP API, CORS middleware, `X-API-Key` enforcement, JPEG header/size bounds validation, bounded drop-oldest `frame_queue`, and FastAPI `lifespan` manager (starts `db`, `worker`, and optional `EMBEDDED_EDGE` controller).
- **Dependencies:** `server.db`, `server.pipeline`, `server.worker` (dynamic import), `edge.controller`.
- **Module State:** `MAX_FRAME_BYTES = 2 MB`, `MAX_JPEG_DIM = 4096`, `ALLOWED_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174"]`, `frame_queue` (`maxsize=QUEUE_SIZE`, default `8`), `queue_lock`, `frames_received_total`, `frames_dropped_total`, `latest_frames`, `latest_frame_device`, `START_TIME`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `_get_jpeg_dimensions` | L23–56 | `_get_jpeg_dimensions(data: bytes) -> Optional[Tuple[int, int]]` | Raw JPEG bytes -> `(width, height)` or `None`; pure function. | Scans JPEG marker segments for SOF headers (`0xC0`–`0xCF`, excluding `0xC4`/`0xC8`/`0xCC`) to extract dimensions without full pixel decompression; stops at SOS (`0xDA`) or malformed segments. |
| `verify_api_key` | L59–88 | `verify_api_key(request: Request = None) -> None` | FastAPI `Request` -> `None` or raises `HTTPException` (`401`/`403`). | Validates `X-API-Key` against `AIIOT_API_KEY`; requires a key whenever bound to `0.0.0.0` or accessed from a non-local client. |
| `DetectionEvent` | L102–111 | `class DetectionEvent(BaseModel)` | Pydantic schema for `POST /events`. | Defines `ts`, `source` (`"api"`), `device_id` (`"sim-01"`), `object_class`, `count`, `avg_conf`, and optional normalized `box`. |
| `AnomalyEvent` | L114–121 | `class AnomalyEvent(BaseModel)` | Pydantic schema for serialized anomaly responses. | Defines `ts`, `device_id`, `rule`, `detail`, and `severity` (`info` / `warning` / `critical`). |
| `lifespan` | L125–143 | `async def lifespan(app: FastAPI)` | Async context manager -> initializes DB, starts/stops worker & embedded edge thread. | Calls `db.init_db()`, starts `worker.start_worker()`, starts `edge_controller.controller` if `EMBEDDED_EDGE == "1"`, and cleanly stops both on shutdown. |
| `post_frames` | L156–213 | `POST /frames` (`202`) | Query (`device_id`, `ts`, `seq`, `source_kind`) + raw JPEG body -> `{status, queue_depth, dropped_oldest}`; mutates `pipeline.devices` and `frame_queue`. | Rejects oversized `Content-Length` before reading (`413`), checks body `<= 2 MB`, verifies JPEG magic bytes (`\xff\xd8`) and dimensions (`<= 4096×4096`), registers frame receipt, drops oldest frame if queue is full, and enqueues the tuple. |
| `post_events` | L217–242 | `POST /events` | `DetectionEvent` JSON -> `{status: "logged", anomalies: [...]}`; mutates rules/DB/alerts. | Converts an injected detection into internal format and runs `pipeline.ingest_detections()` synchronously so synthetic tests and edge-inference clients share the live rule engine. |
| `get_events` | L246–252 | `GET /events` | `limit` (`1..1000`), `object_class`, `device_id` -> list of event dicts. | Queries `db.recent_events()` newest-first for the Detection Ledger UI or API consumers. |
| `get_anomalies` | L256–261 | `GET /anomalies` | `limit` (`1..1000`), `device_id` -> list of anomaly dicts. | Queries `db.recent_anomalies()` newest-first for the Anomaly Vault UI and active banner. |
| `get_latest_frame` | L265–273 | `GET /frames/latest` | Optional `device_id` -> `image/jpeg` `Response` or `404`. | Serves the most recent annotated JPEG from `latest_frames` (defaulting to `latest_frame_device` or first available key). |
| `get_devices` | L277–288 | `GET /devices` | None -> list of device summaries (acquires `pipeline.ingest_lock`). | Snapshots registered devices from `pipeline.devices` with `device_id`, `last_seen_ts`, `frames_received`, and `source_kind`. |
| `get_stats` | L292–311 | `GET /stats` | None -> telemetry dict (reads `db.stats()` and `queue_lock`). | Merges SQLite event/rule/FPS/latency metrics with uptime, current `queue_depth`, `frames_received`, and `frames_dropped`. |
| `get_health` | L315–341 | `GET /health` | None -> `200 ok` or `503 degraded` (`HTTPException`). | Verifies that the background `cv-worker` thread is alive and `yolo26n.onnx` exists on disk. |
| `EdgeConfigUpdate` | L344–360 | `class EdgeConfigUpdate(BaseModel)` | Pydantic schema for `/edge/config` (`fps`, `width`, `quality`, `source`, `device_id`, `streaming`). | Enforces numeric bounds (`fps` `0.5..30`, `width` `160..1920`, `quality` `10..100`) and validates `source` via `check_allowed_source`. |
| `EdgeConfigUpdate.check_allowed_source` | L356–360 | `@field_validator("source") check_allowed_source(cls, v)` | Optional string -> validated source string or raises `ValueError`. | Delegates to `edge_controller.validate_source()` to block path traversal and non-allowlisted URI schemes. |
| `get_edge_status` | L364–366 | `GET /edge/status` | None -> edge status dict. | Returns `edge_controller.controller.get_status()` for the `:5174` Edge Emitter UI. |
| `post_edge_config` | L370–376 | `POST /edge/config` | `EdgeConfigUpdate` -> updated edge status or `400`. | Applies live source/encoder updates to `edge_controller.controller`, converting `ValueError` to `400`. |
| `get_edge_frame` | L380–385 | `GET /edge/frame` | None -> `image/jpeg` `Response` or `404`. | Serves the latest raw pre-inference JPEG captured by the embedded edge emitter. |
| `ModeUpdate` | L388–392 | `class ModeUpdate(BaseModel)` | Pydantic schema (`mode`: `home`/`public`, optional `arming`). | Validates allowed deployment mode and home arming states for `POST /mode`. |
| `get_mode` | L396–398 | `GET /mode` | None -> `{mode, arming}`. | Returns current operating mode and arming state from `pipeline.get_active_mode()`. |
| `post_mode` | L402–408 | `POST /mode` | `ModeUpdate` -> `{mode, arming}` or `400`. | Switches active mode/arming across `pipeline` and all active `RuleEngine` instances. |

---

### 1.2 [`server/pipeline.py`](../server/pipeline.py) (159 LOC)
- **Role:** Unified ingestion seam merging `worker.py` detections and `POST /events` injections under a single `threading.Lock` (`ingest_lock`).
- **Dependencies:** `server.agent`, `server.alerts`, `server.db`, `server.rules`, `config.yaml`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `load_config` | L14–19 | `load_config() -> dict` | Reads `config.yaml` -> parsed `dict` (or `{}`). | Safely loads `config.yaml` via `yaml.safe_load` if present in the working directory. |
| `DeviceState` | L23–36 | `@dataclass class DeviceState` | Holds per-device `rule_engine`, `last_seen`, `frames_received`, `source_kind`, `last_logged_by_class`. | Stores isolated tracking, rule cooldown, and DB debounce state for each `device_id`. |
| `DeviceState.tracker` | L34–36 | `@property def tracker(self)` | None -> `Tracker`. | Convenience accessor returning `self.rule_engine.tracker`. |
| `get_active_mode` | L43–48 | `get_active_mode() -> dict` | None -> `{"mode": ..., "arming": ...}`. | Reads active `mode` (`"public"` default) and `arming` (`"armed_night"` default) from `_cfg`. |
| `set_active_mode` | L51–65 | `set_active_mode(mode: str, arming: Optional[str] = None) -> dict` | `mode`, optional `arming` -> updated mode dict; mutates `_cfg` and active engines under `ingest_lock`. | Validates mode/arming strings and propagates updates live to every registered `DeviceState.rule_engine`. |
| `_get_device` | L68–89 | `_get_device(device_id: str, ts: float, source_kind: str) -> DeviceState` | `device_id`, `ts`, `source_kind` -> `DeviceState`; mutates `devices` dict. | Fetches or lazily initializes a device's `RuleEngine` from `_cfg` (`rules`, `home`, `public`) and updates `last_seen`/`source_kind`. |
| `register_frame_received` | L92–97 | `register_frame_received(device_id: str, ts: float, source_kind: str) -> DeviceState` | `device_id`, `ts`, `source_kind` -> `DeviceState` under `ingest_lock`. | Registers incoming frames at `POST /frames` time and increments `frames_received`. |
| `ingest_detections` | L100–159 | `ingest_detections(device_id, ts, detections, source="api", frame_bgr=None) -> List[Anomaly]` | Detection dicts + timestamp -> `List[Anomaly]`; writes SQLite, fires alerts/agent. | Under `ingest_lock`: groups detections by class, inserts debounced events (`debounce_seconds`), evaluates `RuleEngine.update()`, and dispatches anomalies either to `agent.submit_review()` (when enabled + `NVIDIA_API_KEY` set) or directly to `db.insert_anomaly()` + `alerts.fire()`. |

---

### 1.3 [`server/worker.py`](../server/worker.py) (151 LOC)
- **Role:** Background daemon thread (`cv-worker`) pulling JPEGs from `frame_queue`, running ONNX inference, drawing bounding-box overlays, and recording per-frame latency metrics.
- **Dependencies:** `server.alerts`, `server.app`, `server.db`, `server.detector`, `server.pipeline`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `_get_detector` | L22–31 | `_get_detector() -> Optional[ONNXRuntimeDetector]` | None -> cached `ONNXRuntimeDetector` or `None`; mutates `_detector`. | Lazily instantiates the singleton ONNX detector using `conf_stay` and `class_thresholds` when `yolo26n.onnx` exists. |
| `_annotate_frame` | L34–72 | `_annotate_frame(frame: np.ndarray, detections: list, alert_active: bool) -> bytes` | BGR frame, detections, alert boolean -> JPEG bytes (`quality=80`). | Draws bounding boxes + confidence labels (orange for `watch_classes`, green otherwise) and overlays an 8px red border + `"ALERT ACTIVE"` banner when an alert is active. |
| `_worker_loop` | L75–127 | `_worker_loop() -> None` | Reads `frame_queue` -> updates `latest_frames` and SQLite `frame_metrics`. | Initializes worker SQLite connection, optionally skips frames per `process_every_n_frames`, decodes JPEG (`<=4096×4096`), times `det_engine.detect()`, invokes `pipeline.ingest_detections()`, saves annotated JPEG, and records `inference_ms` and `e2e_ms`. |
| `start_worker` | L130–137 | `start_worker() -> None` | None -> spawns daemon `cv-worker` thread. | Resets `_stop_event` and starts `_worker_loop` if not already running. |
| `stop_worker` | L140–146 | `stop_worker(timeout: float = 2.0) -> None` | `timeout` -> joins and clears `_worker_thread`. | Signals `_stop_event` and waits up to `timeout` seconds for clean worker shutdown. |
| `is_running` | L149–151 | `is_running() -> bool` | None -> `bool`. | Reports whether `_worker_thread` is instantiated and currently alive. |

---

### 1.4 [`server/detector.py`](../server/detector.py) (117 LOC)
- **Role:** CPU-only ONNX Runtime object detector (`yolo26n.onnx`, NMS-free `(1, 300, 6)` output tensor).
- **Dependencies:** `onnxruntime`, `cv2`, `numpy`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `COCO_NAMES` | L7–26 | `Dict[int, str]` (80 classes) | Fallback class-ID-to-label mapping. | Maps COCO indices `0..79` when ONNX custom metadata lacks a `names` table. |
| `ONNXRuntimeDetector.__init__` | L32–59 | `__init__(self, model_path="yolo26n.onnx", conf=0.30, class_thresholds=None, allowed_classes=None)` | Loads ONNX session with `CPUExecutionProvider`. | Initializes ORT session, resolves input tensor name, and parses embedded class `names` metadata (falling back to `COCO_NAMES`). |
| `ONNXRuntimeDetector.detect` | L61–117 | `detect(self, frame_bgr: np.ndarray, allowed_classes: Optional[Set[str]] = None) -> List[dict]` | BGR frame -> list of `{class_name, conf, box}` (boxes normalized `0..1`). | Letterboxes input to `640×640` (`114` gray pad), converts BGR→RGB NCHW float32 `/255`, runs ORT inference, filters by `allowed_classes` and per-class confidence threshold, and reverses letterbox padding back to normalized image coordinates. |

---

### 1.5 [`server/tracker.py`](../server/tracker.py) (286 LOC)
- **Role:** Greedy IoU/centroid tracker for both `person` and watch-list objects with confidence hysteresis (`conf_enter`/`conf_stay`), occlusion persistence (`track_timeout=15s`), owner binding, and stationary proximity resets.
- **Dependencies:** Standard library (`math`, `dataclasses`, `typing`).

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `box_center` | L9–11 | `box_center(b: Box) -> Tuple[float, float]` | Normalized box `(x1, y1, x2, y2)` -> `(cx, cy)`. | Computes the geometric midpoint of a bounding box. |
| `box_bottom_center` | L14–16 | `box_bottom_center(b: Box) -> Tuple[float, float]` | Normalized box -> `(cx, y2)`. | Computes bottom-center foot coordinates used for person polygon zone tests. |
| `center_distance` | L19–23 | `center_distance(a: Box, b: Box) -> float` | Two boxes -> Euclidean distance. | Measures normalized distance between centers of boxes `a` and `b`. |
| `box_iou` | L26–37 | `box_iou(a: Box, b: Box) -> float` | Two boxes -> IoU in `[0.0, 1.0]`. | Computes Intersection-over-Union, returning `0.0` when non-overlapping or degenerate. |
| `Track` | L41–69 | `@dataclass class Track` | Per-object/person state container. | Tracks `first_seen`, `last_seen`, `box`, `anchor_box`, `last_person_near_ts`, `track_id`, `owner_id`, `last_near_person_id`, `hits`, `history`, `near_since`, and `zone_entered_ts`. |
| `Track.speed` | L59–69 | `speed(self, window_s: float = 1.5) -> float` | `window_s` -> normalized units/sec. | Computes center displacement rate between oldest and newest samples inside `window_s`. |
| `Tracker.__init__` | L75–92 | `__init__(self, track_timeout=15.0, owner_radius=0.20, conf_enter=0.40, conf_stay=0.30, confirm_frames=1)` | Configures matching/lifetime thresholds. | Initializes active watch-class `tracks`, `person_tracks`, `recently_pruned` (30s buffer), and ID allocator. |
| `Tracker._alloc_id` | L94–98 | `_alloc_id(self) -> int` | None -> sequential `int`. | Returns the next unique `track_id` and increments `_next_id`. |
| `Tracker._update_person_tracks` | L100–149 | `_update_person_tracks(self, person_dets, ts) -> List[Track]` | Person `(box, conf)` list + `ts` -> currently visible person `Track`s. | Prunes expired person tracks, greedily matches detections (`conf >= conf_stay`) by `(IoU, -dist)`, creates new tracks at `conf >= conf_enter`, and retains 5s position history. |
| `Tracker._is_person_stationary` | L152–157 | `@staticmethod _is_person_stationary(ptr: Track, ts: float, window_s: float = 2.0) -> bool` | Person `Track`, `ts`, `window_s` -> `bool`. | Returns `True` if the person's center moved `<= 0.10` over the lookback window. |
| `Tracker.update` | L159–286 | `update(self, detections, ts, watch_classes=None) -> List[Track]` | Normalized detections + `ts` -> confirmed watch-class `Track`s. | Prunes stale tracks, updates person tracks, matches watch-list objects with hysteresis, updates 5s `anchor_box` (resetting `last_person_near_ts` on displacement `IoU < 0.3` **only** when a person is within `owner_radius`), and resets the unattended timer only for the bound `owner_id` or a stationary person present `>= 2.0s`. |

---

### 1.6 [`server/rules.py`](../server/rules.py) (919 LOC)
- **Role:** Pure-logic anomaly rule engine supporting `public` (21 rules), `home` (18 rules), and shared camera health / tamper / repeat escalation rules (`S1`–`S6`), with per-`(rule, track_id, zone)` cooldown and LangGraph policy tagging.
- **Dependencies:** `cv2`, `numpy`, `server.tracker`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `Anomaly` | L11–20 | `@dataclass class Anomaly` | Output event object (`rule`, `detail`, `severity`, `ts`, `policy`, `zone`, `mode`). | Encapsulates a fired rule event and its routing policy (`always_alert`, `review`, or `log_only`). |
| `_escalate_severity` | L43–46 | `_escalate_severity(sev: str) -> str` | Severity string -> next tier in `["info", "warning", "critical"]`. | Bumps anomaly severity by one step for repeat-escalation (`S5`), capped at `"critical"`. |
| `point_in_polygon` | L49–54 | `point_in_polygon(pt: Tuple[float, float], polygon: List[List[float]]) -> bool` | `(x, y)` + polygon vertices -> `bool`. | Uses `cv2.pointPolygonTest` to test whether a normalized point falls inside or on a polygon (`>= 3` vertices). |
| `_parse_hhmm` | L57–60 | `_parse_hhmm(s: str) -> int` | `"HH:MM"` -> integer minutes since `00:00`. | Parses clock strings from `config.yaml` time windows. |
| `is_in_time_window` | L63–72 | `is_in_time_window(ts: float, start_hhmm: str, end_hhmm: str) -> bool` | Epoch `ts`, start/end strings -> `bool`. | Checks if local wall-clock time falls inside a daytime or overnight (`start > end`) window. |
| `_cross_side` | L75–77 | `_cross_side(p1, p2, pt) -> float` | Two line endpoints + point -> signed cross product. | Determines which half-plane of directed tripwire `p1 -> p2` a point sits on. |
| `RuleEngine.__init__` | L83–142 | `__init__(self, config=None, mode=None, arming=None, home_cfg=None, public_cfg=None)` | Loads thresholds, mode/arming, and instantiates `Tracker`. | Initializes rule parameters, tamper baselines, crowd/zone histories, and `last_fired` cooldown map. |
| `RuleEngine.set_mode` | L144–157 | `set_mode(self, mode: str, arming: Optional[str] = None) -> None` | Switches between `"home"` and `"public"` and updates `arming`. | Recomputes `watch_classes` and `ignore_classes` dynamically for the active mode. |
| `RuleEngine._can_fire` | L159–162 | `_can_fire(self, key: object, ts: float) -> bool` | Cooldown key + `ts` -> `bool`. | Enforces `cooldown_seconds` (`10.0s` default) independently per `(rule, track_id, zone)` tuple. |
| `RuleEngine._policy_for` | L164–170 | `_policy_for(self, rule: str) -> str` | Rule name -> `"always_alert"`, `"log_only"`, or `"review"`. | Looks up whether `agent.py` must always alert, log silently, or send to LLM triage. |
| `RuleEngine._emit` | L172–207 | `_emit(self, out, rule, detail, severity, ts, track_id=None, zone="", policy=None)` | Appends `Anomaly` to `out` if cooldown allows; updates `fire_history`. | Enforces cooldown, tracks repeat fires within `repeat_escalation_window_s` (`S5`), escalates severity when count reaches threshold, and appends `Anomaly`. |
| `RuleEngine.check_camera_health` | L209–255 | `check_camera_health(self, frame_bgr: Optional[np.ndarray], ts: float) -> List[Anomaly]` | Raw BGR frame + `ts` -> camera tamper anomalies. | Emits `camera_tamper_blocked` (`S2`, mean luminance `< tamper_dark_lum` or Laplacian blur variance `< tamper_blur_var` for `>= 5s`) and `camera_tamper_moved` (`S3`, grayscale histogram correlation diff `> 0.65` for `>= 5s`, updating EMA `ref_hist` otherwise). |
| `RuleEngine.check_offline` | L257–268 | `check_offline(self, now_ts: float) -> List[Anomaly]` | Current timestamp -> `List[Anomaly]`. | Emits `camera_offline` (`S1`, critical) when gap since `last_frame_ts` reaches `offline_seconds`. |
| `RuleEngine.update` | L270–320 | `update(self, detections: List[dict], ts: float, frame_bgr: Optional[np.ndarray] = None) -> List[Anomaly]` | Frame detections + `ts` + optional image -> `List[Anomaly]`. | Updates `last_frame_ts`, runs `check_camera_health`, bypasses security rules when `home` + `disarmed` (`S6`), updates `Tracker`, and dispatches to `_eval_home` or `_eval_public`. |
| `RuleEngine._eval_home` | L322–584 | `_eval_home(self, anomalies, detections, visible_persons, active_tracks, person_count, ts) -> None` | Mutates `anomalies` list with home-mode triggers. | Evaluates night presence (`H2`), zones (`H1` `person_in_zone`, `H14` `fence_or_wall_approach`, `H3` `loitering`, `H18` `child_near_hazard_zone`, `H5` `multiple_persons_entry`, `H15` `repeat_visit_casing`), tripwires (`H4` `zone_entry_exit`), packages/valuables (`H6`, `H7`, `H8`), vehicles (`H11`, `H12`), falls/inactivity (`H9` `person_down`, `H10` `prolonged_inactivity`), sharp objects (`H13`), and lone pets in hazard zones (`H17`) while ignoring pets (`H16`). |
| `RuleEngine._eval_public` | L586–866 | `_eval_public(self, anomalies, detections, visible_persons, active_tracks, person_count, ts) -> None` | Mutates `anomalies` list with public-mode triggers. | Evaluates occupancy/crowd (`R1`/`P1` `occupancy_spike`, `P8` `rapid_gathering`, `P9` `sudden_dispersal`, `P20` `after_hours_presence`), unattended items (`R2`/`P2` `unexpected_object`, `R3`/`P3` `object_dwell`, `P4` `abandoned_after_owner_left`, `P17` `bag_taken_by_other_person`, `P16` `multiple_unattended_objects`), person behavior (`P10`, `P11`, `P12`), zones (`P5`, `P7`, `P18`, `P13`, `P15`), tripwires (`P6`, `P19`), and sharp objects (`P21`). |
| `RuleEngine._check_lines` | L868–919 | `_check_lines(self, anomalies, visible_persons, lines, ts, rule_name, capacity_limit=None) -> None` | Tracks cross-product sign transitions per `(track_id, line)`. | Detects line crossings (`left_to_right` / `right_to_left`), updates `net_capacity_count`, emits `zone_entry_exit` or `wrong_way_or_tripwire`, and checks `capacity_exceeded`. |

---

### 1.7 [`server/db.py`](../server/db.py) (211 LOC)
- **Role:** Zero-ORM SQLite persistence layer (`events.db`) using thread-local connections, WAL concurrency (`busy_timeout=5000`), and parameterized SQL.
- **Tables:** `events`, `anomalies`, `frame_metrics` (with `idx_events_ts`, `idx_anomalies_ts`, `idx_metrics_ts`).

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `_conn` | L10–21 | `_conn() -> sqlite3.Connection` | Returns thread-local connection; opens DB + sets WAL if missing or `DB_PATH` changed. | Ensures safe per-thread SQLite access with `sqlite3.Row` factory and `WAL` pragmas. |
| `init_db` | L24–68 | `init_db(db_path: Optional[str] = None) -> None` | Optional `db_path` -> creates tables and indexes. | Optionally overrides `DB_PATH` and executes idempotent `CREATE TABLE IF NOT EXISTS` DDL for all three tables. |
| `insert_event` | L71–86 | `insert_event(ts, device_id, source, object_class, count, avg_conf) -> int` | Event fields -> inserted `id` (`int`). | Inserts a debounced object detection row into `events` and commits immediately. |
| `insert_anomaly` | L89–103 | `insert_anomaly(ts, device_id, rule, detail, severity) -> int` | Anomaly fields -> inserted `id` (`int`). | Persists a triggered or `[SUPPRESSED]` anomaly row into `anomalies`. |
| `insert_frame_metric` | L106–120 | `insert_frame_metric(ts, device_id, frame_bytes, inference_ms, e2e_ms) -> int` | Performance metrics -> inserted `id` (`int`). | Logs per-frame bandwidth (`frame_bytes`), ONNX inference time, and end-to-end latency. |
| `recent_events` | L123–142 | `recent_events(limit=100, object_class=None, device_id=None) -> List[Dict[str, Any]]` | Filters + clamped `limit` (`1..1000`) -> newest-first list of dicts. | Queries `events` ordered by `ts DESC, id DESC`. |
| `recent_anomalies` | L145–160 | `recent_anomalies(limit=100, device_id=None) -> List[Dict[str, Any]]` | Optional `device_id` + clamped `limit` -> newest-first list of dicts. | Queries `anomalies` ordered by `ts DESC, id DESC`. |
| `stats` | L163–211 | `stats(now: Optional[float] = None) -> Dict[str, Any]` | Optional `now` -> aggregated telemetry dict. | Computes `total_events`, rule counts (`occupancy_spike`, `unexpected_object`, `object_dwell`), `last_anomaly_ts`, 10s rolling `fps`, and 60s rolling `avg_frame_kb`, `avg_inference_ms`, and `avg_e2e_ms`. |

---

### 1.8 [`server/alerts.py`](../server/alerts.py) (115 LOC)
- **Role:** Alert actuation channel — maintains 15s red-overlay active window, prints ANSI terminal banners, triggers OS beep, and delivers HMAC-SHA256 signed webhooks.
- **Dependencies:** `requests`, `hmac`, `hashlib`, `winsound` (Windows) / `afplay` (macOS).

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `is_alert_active` | L17–20 | `is_alert_active(now: float | None = None) -> bool` | Optional `now` -> `bool`. | Returns `True` while `now < alert_active_until` so `worker.py` renders the red `"ALERT ACTIVE"` frame border. |
| `_beep` | L23–43 | `_beep() -> None` | None -> audible alert side effect. | Plays `winsound.Beep(1000, 250)` on Windows, `afplay` Ping on macOS, or terminal bell `\a` elsewhere. |
| `send_hermes_webhook` | L46–96 | `send_hermes_webhook(anomaly, device_id="", reason="", webhook_url=None, webhook_secret=None) -> bool` | Anomaly + optional overrides -> `bool` HTTP `<300` status. | Signs JSON alert payload with HMAC-SHA256 (`X-Hub-Signature-256`) using `HERMES_WEBHOOK_SECRET` and POSTs to `HERMES_WEBHOOK_URL` (3s timeout); returns `False` if secret is unset. |
| `fire` | L99–115 | `fire(anomaly, device_id: str = "", reason: str = "") -> None` | Anomaly + metadata -> updates `alert_active_until` (`+15s`), console, beep, webhook. | Activates the 15s overlay timer, logs colored banner to stdout, plays `_beep()`, and triggers `send_hermes_webhook()`. |

---

### 1.9 [`server/agent.py`](../server/agent.py) (232 LOC)
- **Role:** LangGraph metadata-only security triage workflow (never inspects images) with fail-open guarantees and async `ThreadPoolExecutor` dispatch.
- **Dependencies:** `langgraph.graph`, `langchain_openai.ChatOpenAI`, `langchain_ollama.ChatOllama`, `dotenv`, `server.alerts`, `server.db`, `server.rules`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `AgentState` | L21–34 | `class AgentState(TypedDict, total=False)` | Typed state dictionary shared across graph nodes. | Carries `device_id`, `anomaly`, `mode`, `arming`, `policy`, `recent_events`, `local_time`, `real`, `severity`, `reason`, and `action`. |
| `_extract_json` | L37–43 | `_extract_json(text: str) -> dict` | Raw LLM text -> parsed `dict`. | Uses regex `\{.*\}` (`DOTALL`) to strip surrounding prose before `json.loads`. |
| `_default_llm_invoke` | L46–77 | `_default_llm_invoke(prompt: str, cfg: dict) -> str` | Prompt + config -> raw model completion text. | Dispatches to `ChatOllama` (`provider == "ollama"`) or `ChatOpenAI` (NVIDIA Integrate API via `NVIDIA_API_KEY`, `temperature=0`, `max_retries=0`). |
| `build_agent_graph` | L80–197 | `build_agent_graph(cfg=None, llm_fn=None)` | Returns compiled LangGraph `StateGraph` (`context -> decide -> notify | suppress -> END`). | Constructs the triage graph: `context_node` (L83–96) queries last 5 events; `decide_node` (L98–144) obeys `log_only`/`always_alert` policies and fails open on LLM errors; `route_edge` (L146–147) routes to `notify_node` (L149–161, DB + `alerts.fire`) or `suppress_node` (L163–173, logs `[SUPPRESSED]` info row). |
| `review_anomaly` | L200–217 | `review_anomaly(anomaly, device_id, mode="public", arming="armed_night", agent_cfg=None, llm_fn=None) -> Dict[str, Any]` | Single `Anomaly` -> final `AgentState` dict. | Builds and synchronously executes the compiled LangGraph triage graph for one anomaly. |
| `submit_review` | L220–232 | `submit_review(anomaly, device_id, mode="public", arming="armed_night", agent_cfg=None) -> None` | Submits `review_anomaly` to `_executor` or runs inline. | Enqueues triage onto the 2-worker `ThreadPoolExecutor` when `async_dispatch` is `True` (default) to avoid blocking the CV worker. |

---

## 2. Edge Capture & Streaming (`edge/`)

### 2.1 [`edge/capture.py`](../edge/capture.py) (97 LOC)
- **Role:** Abstraction over local webcams, auto-looping MP4 files, RTSP/HTTP feeds, and live YouTube streams (`yt-dlp`).
- **Dependencies:** `cv2`, `numpy`, `yt_dlp` (lazy import).

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `resolve_youtube_stream_url` | L8–23 | `resolve_youtube_stream_url(url: str) -> str` | YouTube URL -> direct stream URL (`<=720p`). | Uses `yt_dlp.YoutubeDL(..., download=False)` (with Node JS runtime if present) to obtain a playable media URL without downloading to disk. |
| `VideoSource.__init__` | L29–68 | `__init__(self, src: str | int)` | Opens `cv2.VideoCapture` or raises `RuntimeError`. | Classifies `src` (`"live"`, `"youtube"`, `"url"`, or `"file"`), configures single-frame capture buffer on webcams, and stores `file_fps`. |
| `VideoSource.read` | L70–92 | `read(self) -> np.ndarray | None` | Reads next BGR frame or `None`. | Loops local MP4 files back to frame `0` on EOF and re-resolves YouTube stream URLs when connections drop. |
| `VideoSource.release` | L94–97 | `release(self) -> None` | Releases OpenCV `VideoCapture` handle. | Frees camera/stream resources cleanly on stop or source hot-swap. |

---

### 2.2 [`edge/controller.py`](../edge/controller.py) (288 LOC)
- **Role:** Thread-safe embedded edge streamer (`controller` singleton) serving `/edge/*` endpoints and writing `data/edge_state.json`.
- **Dependencies:** `edge.capture.VideoSource`, `cv2`, `requests`, `yaml`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `load_defaults` | L13–27 | `load_defaults() -> dict` | Reads `config.yaml` `edge` block -> defaults dict. | Initializes `source` (`data/demo.mp4` if present else `"0"`), `device_id`, `fps`, `width`, `quality`, and `streaming=True`. |
| `validate_source` | L30–50 | `validate_source(src: str) -> str` | Raw source string -> sanitized string or `ValueError`. | Restricts sources to numeric camera indices, `http/https/rtsp` URLs, or `.mp4` files directly inside `data/` (blocking directory traversal). |
| `save_state_file` | L53–66 | `save_state_file(state: dict) -> None` | Writes `data/edge_state.json` atomically via temp file + `os.replace`. | Persists live configuration changes so standalone `edge_client.py` processes hot-reload settings safely. |
| `EdgeEmitterController.__init__` | L72–88 | `__init__(self, server_url="http://127.0.0.1:8000")` | Initializes lock, config, telemetry counters, and `edge_state.json`. | Prepares embedded edge streaming state before `start()`. |
| `EdgeEmitterController.start` | L90–96 | `start(self) -> None` | Spawns daemon `_run_loop` thread if inactive. | Starts background frame capture and HTTP uplink. |
| `EdgeEmitterController.stop` | L98–103 | `stop(self, timeout: float = 2.0) -> None` | Sets `_stop` and joins thread. | Cleanly stops the embedded emitter during server shutdown. |
| `EdgeEmitterController.update_config` | L105–114 | `update_config(self, updates: dict) -> dict` | Config patch -> `get_status()` dict; persists `edge_state.json`. | Validates `source`, applies allowed keys under lock, saves state file, and returns full status. |
| `EdgeEmitterController.list_sources` | L116–160 | `list_sources(self) -> list[dict]` | Scans `data/*.mp4` -> preset + file list with scenario tags. | Populates the Edge Deck source selector with annotated demo scenarios and webcam `0`. |
| `EdgeEmitterController.get_status` | L162–176 | `get_status(self) -> dict` | Snapshot of config, FPS, KB/s, queue depth, errors, and sources. | Serves `/edge/status` telemetry to the `:5174` UI. |
| `EdgeEmitterController._run_loop` | L178–285 | `_run_loop(self) -> None` | Background capture/encode/POST loop. | Hot-swaps `VideoSource`, honors `streaming` pause flag, throttles to `fps`, resizes aspect-preserving, JPEG-encodes, caches `latest_jpeg`, POSTs to `/frames` with optional `X-API-Key`, and updates 4s rolling stats. |

---

### 2.3 [`edge/edge_client.py`](../edge/edge_client.py) (175 LOC)
- **Role:** Standalone CLI edge capture process (for separate terminal or Raspberry Pi), supporting live hot-reload from `data/edge_state.json`.
- **Dependencies:** `edge.capture.VideoSource`, `cv2`, `requests`, `yaml`.

| Symbol | Lines | Signature / Role | Inputs -> Outputs & Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `load_edge_defaults` | L16–21 | `load_edge_defaults() -> dict` | Reads `config.yaml` `edge` section -> `dict`. | Provides CLI default values for `--device-id`, `--fps`, `--width`, and `--quality`. |
| `read_runtime_state` | L24–32 | `read_runtime_state() -> dict | None` | Reads `data/edge_state.json` -> `dict` or `None`. | Safely parses runtime control overrides without crashing on missing or partial files. |
| `main` | L35–171 | `main()` | Parses CLI flags -> streams JPEG frames until `--duration` or `Ctrl+C`. | Checks `data/edge_state.json` every `0.4s` for source/encoder hot-swaps, throttles/resizes/JPEG-encodes frames, POSTs to `/frames` (with `X-API-Key` and exponential backoff `0.5s`–`5.0s`), and prints 5s window throughput logs. |

---

## 3. Frontend (`frontend/`)

### 3.1 [`frontend/index.html`](../frontend/index.html) (18 LOC) & [`frontend/vite.config.js`](../frontend/vite.config.js) (14 LOC) & [`frontend/package.json`](../frontend/package.json) (19 LOC)
- **`index.html`:** Loads Google Fonts (`Instrument Serif`, `JetBrains Mono`, `Plus Jakarta Sans`), mounts `#root`, and loads `/src/main.jsx`.
- **`vite.config.js`:** Enables `@vitejs/plugin-react`, binds `server.host = '0.0.0.0'`, and exposes `import.meta.env.VITE_API_KEY` from `process.env.VITE_API_KEY || process.env.AIIOT_API_KEY`.
- **`package.json`:** Defines React 18.3.1, Vite 6.0.5, `dev:analytics` (`:5173`), `dev:edge` (`:5174`), and `build`.

### 3.2 [`frontend/src/main.jsx`](../frontend/src/main.jsx) (25 LOC)
- **Role:** Dual-app frontend entry router.
- **Behavior (L11–25):** Inspects `window.location.port === '5174'`, `?app=edge`, or `VITE_APP_ROLE === 'edge'`, sets `document.title`, and renders `<EdgeEmitterApp />` or `<AnalyticsApp />` inside `<React.StrictMode>`.

### 3.3 [`frontend/src/components/GlassShell.jsx`](../frontend/src/components/GlassShell.jsx) (132 LOC)
- **Role:** Shared RoastGlass UI chrome components used by both `:5173` and `:5174`.

| Symbol | Lines | Signature / Role | State / Effects | What It Does |
| --- | --- | --- | --- | --- |
| `CustomCursor` | L6–57 | `export function CustomCursor()` | `dotRef`, `ringRef`, `mousemove` listener + `requestAnimationFrame` loop. | Renders a crisp pointer dot and spring-eased trailing ring (`0.24` lerp) that enlarges (`.is-hover`) over buttons, links, inputs, selects, and `.source-item` elements. |
| `AnimatedTabBar` | L62–110 | `export function AnimatedTabBar({ tabs, activeTab, onChange })` | `sliderStyle` state, `barRef`, `btnRefs`, `resize` listener. | Measures the active tab button via `getBoundingClientRect()` and animates the pill slider (`width` + `translateX`) across tab switches and resizes. |
| `HeroHeader` | L115–132 | `export function HeroHeader({ badge, title, subtitle, peerUrl, peerLabel })` | Pure presentational component. | Displays the top glass header with pulsing role pill, serif heading, subtitle, and external peer-console switch button. |

### 3.4 [`frontend/src/AnalyticsApp.jsx`](../frontend/src/AnalyticsApp.jsx) (426 LOC)
- **Role:** Server Analytics Console (`:5173`) consuming live CV telemetry, annotated JPEG video, anomalies, detection ledger, and node health.
- **Endpoints Polled:** `GET /stats`, `/anomalies?limit=60`, `/events?limit=120`, `/devices`, `/health` (every `650 ms`), and `/frames/latest` (every `260 ms`).

| Symbol | Lines | Signature / Role | State / Hooks / Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `apiHeaders` | L8 | `const apiHeaders = (extra = {}) => ...` | Reads `VITE_API_KEY`. | Returns HTTP headers object injecting `X-API-Key` when configured. |
| `TABS` | L10–15 | `const TABS = [...]` | Constant config. | Defines the four dashboard tabs: `live`, `anomalies`, `events`, and `nodes`. |
| `OccupancyChart` | L20–83 | `function OccupancyChart({ events })` | Pure SVG component. | Filters up to 32 recent `'person'` detection events chronologically and plots an SVG area/line timeline alongside a dashed red R1 threshold reference line (`>3 persons`). |
| `AnalyticsApp` | L88–426 | `export default function AnalyticsApp()` | `activeTab`, `stats`, `anomalies`, `events`, `devices`, `health`, `frameUrl`; 2 `useEffect` polling loops. | Polls telemetry JSON every `650 ms` (`Promise.all`), swaps annotated JPEG Blob URLs every `260 ms` without flicker (revoking old URLs), triggers the active 15s alert banner, and renders the 6 KPI tiles plus 4 navigable views. |

### 3.5 [`frontend/src/EdgeEmitterApp.jsx`](../frontend/src/EdgeEmitterApp.jsx) (477 LOC)
- **Role:** Edge Emitter Control Deck (`:5174`) for hot-swapping input video feeds, tuning compression/FPS, and injecting synthetic R1/R2/R3 events.
- **Endpoints Used:** `GET /edge/status` (`500 ms`), `GET /edge/frame` (`260 ms`), `POST /edge/config`, `POST /events`.

| Symbol | Lines | Signature / Role | State / Hooks / Side Effects | What It Does |
| --- | --- | --- | --- | --- |
| `apiHeaders` | L8 | `const apiHeaders = (extra = {}) => ...` | Reads `VITE_API_KEY`. | Injects `X-API-Key` on outgoing fetch requests when present. |
| `TABS` | L10–14 | `const TABS = [...]` | Constant config. | Defines the three control deck tabs: `source`, `encoder`, and `inject`. |
| `EdgeEmitterApp` | L19–477 | `export default function EdgeEmitterApp()` | `activeTab`, `edge`, `customSrc`, `showCustomInput`, `frameUrl`, `toastMsg`; 2 `useEffect` hooks. | Polls `/edge/status` (`500 ms`) and raw `/edge/frame` (`260 ms`, Blob URL swap), and renders 6 live uplink KPI cards plus the Source, Encoder, and Synthetic Injector tabs. |
| `showToast` | L42–45 | `const showToast = (msg) => ...` | Sets `toastMsg` + `3200 ms` timeout. | Displays a temporary green confirmation toast for source swaps, config saves, and event injections. |
| `updateEdgeConfig` | L48–63 | `const updateEdgeConfig = async (patch, label) => ...` | `POST /edge/config` -> updates `edge` state. | Pushes partial source, streaming, FPS, width, quality, or `device_id` changes to the backend controller. |
| `injectEvent` | L114–196 | `const injectEvent = async (type) => ...` | `POST /events` -> shows alert count toast. | Fires synthetic `r1` (5 persons), `r2` (backpack at `t-6s` and `t`), or `r3` (suitcase unattended at `t-31s` and `t`) payloads into `POST /events`. |

### 3.6 [`frontend/src/styles.css`](../frontend/src/styles.css) (540 LOC)
- **Role:** Coffee-Glass ("RoastGlass") dark theme stylesheet defining espresso palette tokens (`:root`), custom cursor styling (`.custom-cursor-dot`, `.custom-cursor-ring`), frosted glass cards (`.glass-card`), animated pill tabs (`.ios-tabbar`, `.ios-tab-slider`), responsive KPI/split grids, video HUD overlay, sticky scrollable tables, and severity pills.

---

## 4. Scripts, Tests & Configuration

### 4.1 [`scripts/eval.py`](../scripts/eval.py) (102 LOC)
- **Role:** Offline clip evaluation harness measuring Precision and Recall of `ONNXRuntimeDetector` + `RuleEngine` against `data/eval_labels.yaml`.

| Symbol | Lines | Signature / Role | What It Does |
| --- | --- | --- | --- |
| `ensure_labels` | L28–36 | `ensure_labels(path: str = "data/eval_labels.yaml") -> dict` | Loads clip labels YAML, or creates `data/eval_labels.yaml` with `DEFAULT_LABELS` if missing. |
| `evaluate_clip` | L39–68 | `evaluate_clip(detector, clip_cfg, base_cfg, sample_fps=5.0) -> set` | Samples video frames at `sample_fps`, runs `detector.detect()` + `RuleEngine.update()`, and collects triggered rule names. |
| `main` | L71–98 | `main() -> int` | Loads `config.yaml`, evaluates every configured clip, tallies TP/FP/FN, and prints Precision and Recall. |

### 4.2 [`scripts/export_model.py`](../scripts/export_model.py) (35 LOC)
- **Role:** One-time model provisioning and ONNX sanity verifier.

| Symbol | Lines | Signature / Role | What It Does |
| --- | --- | --- | --- |
| `main` | L10–27 | `main()` | Exports `yolo26n.pt` via Ultralytics (`nms=False`) or downloads `yolo26n.onnx` from Ultralytics releases, then verifies tensor shapes with `onnxruntime`. |

### 4.3 [`scripts/simulator.py`](../scripts/simulator.py) (66 LOC)
- **Role:** Camera-free synthetic detection generator exercising R1, R2, and R3 against `POST /events`.

| Symbol | Lines | Signature / Role | What It Does |
| --- | --- | --- | --- |
| `run_simulator` | L7–52 | `run_simulator(server_url: str, device_id: str, real_time: bool = True) -> dict` | Runs a 91s 3-phase sequence (`0-29s` normal, `30-59s` 6 persons + backpack, `60-90s` unattended suitcase) posting to `/events` with `X-API-Key` if configured. |
| `main` | L55–62 | `main()` | Parses `--server`, `--device-id`, and `--fast` (no 1s sleep) CLI arguments and runs the simulator. |

### 4.4 [`scripts/test_frontends.js`](../scripts/test_frontends.js) (108 LOC)
- **Role:** Playwright headless Chromium smoke test & screenshot verification for `:5174` and `:5173`.

| Symbol | Lines | Signature / Role | What It Does |
| --- | --- | --- | --- |
| `run` | L8–103 | `async function run()` | Launches headless Chromium (`1440×900`), checks custom cursor, tabs, source switching, encoder view, and R1 injector on `:5174`, verifies `:5173` views, and writes screenshots to `screenshots/`. |

### 4.5 [`tests/test_rules.py`](../tests/test_rules.py) (636 LOC)
- **Role:** Pytest suite (25 `test_*` functions + 3 helpers) verifying core R1/R2/R3 rules, tracker edge cases, HTTP API security, home/public extended rules, camera tamper/escalation, LangGraph triage, and Hermes HMAC signing.

| Group / Function | Lines | What It Verifies |
| --- | --- | --- |
| **Helpers:** `make_engine`, `_make_sec_req`, `make_home_engine` | L5–9, L234–259, L456–465 | Constructs `RuleEngine` instances from `config.yaml` (`public` or `home`) and synthetic ASGI `Request` objects for fast unit tests. |
| **Core R1–R3 & Tracker Edge Cases:** `test_ut1_occupancy_spike`, `test_ut2_unexpected_object`, `test_ut3_object_dwell_unattended`, `test_ut4_object_dwell_reset_by_person_near`, `test_passerby_does_not_reset_dwell_timer`, `test_nudge_without_person_does_not_reset_dwell_timer`, `test_bag_occluded_for_4s_keeps_track_and_fires`, `test_two_bags_independent_cooldown`, `test_confidence_hysteresis`, `test_ut5_cooldown` | L12–175 | Thresholds (`>3` persons, `5s` unexpected, `30s` dwell), owner return reset, passerby immunity, wind-nudge immunity, 4s occlusion survival, per-track cooldown independence, `0.40`/`0.30` confidence hysteresis, and `10s` cooldown spacing. |
| **API & Security Gates:** `test_api_frames_and_events`, `test_security_401_missing_api_key`, `test_security_403_invalid_api_key`, `test_security_413_content_length_before_read`, `test_security_400_oversize_jpeg_dimensions`, `test_security_422_edge_config_bounds`, `test_security_422_bad_source`, `test_security_cors_restricted`, `test_api_key_set_accepted_and_sent_by_clients` | L178–453 | `/frames` (`202`/`400`/`413`), `/events`, `/health` `503` checks, `X-API-Key` `401`/`403` + `0.0.0.0` enforcement, pre-read `Content-Length` rejection, JPEG SOF `>4096` guard, `EdgeConfigUpdate` bounds & traversal checks, CORS allowlist, and `simulator.py` header forwarding. |
| **Extended Home/Public, Tamper & Escalation:** `test_home_rules_zone_loiter_night_and_pets`, `test_home_package_left_taken_and_person_down`, `test_public_extended_rules_dispersal_and_zones`, `test_camera_tamper_and_escalation` | L468–547 | Pet ignore + night/zone/loiter in home mode, door package left/taken + `person_down`, public `sudden_dispersal` + `vehicle_in_pedestrian_zone`, `camera_tamper_blocked` on dark frames, and `repeat_escalation` (`warning -> critical`). |
| **Agent & Webhook:** `test_langgraph_agent_triage_and_fail_open`, `test_hermes_webhook_signing` | L550–632 | LangGraph confirm/upgrade, suppress false alarm, fail-open alerting when LLM raises, and HMAC-SHA256 `X-Hub-Signature-256` signing. |

### 4.6 [`config.yaml`](../config.yaml) (188 LOC)
- **Role:** Runtime configuration defining `edge` stream defaults (`edge-01`, `5 fps`, `960px`, `q=90`), `server` thresholds (`queue_size=8`, `conf=0.4`, `conf_stay=0.3`, per-class thresholds, `debounce_seconds=2`), `mode`/`arming`, shared `rules` (including tamper/offline/repeat-escalation), `home` polygons/tripwires/timings, `public` polygons/tripwires/operating hours, and `agent` LLM provider config.
