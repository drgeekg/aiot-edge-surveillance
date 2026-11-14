# Graph Report - AIIot project  (2026-11-14)

## Corpus Check
- Corpus is ~22,323 words - fits in a single context window. You may not need a graph.

## Summary
- 307 nodes · 699 edges · 10 communities
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 44 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Edge Capture & Simulator CLI
- FastAPI Auth & Test Suite
- API Read Endpoints & SQLite DB
- Tracking & Anomaly Rule Engine
- React RoastGlass Web Frontend
- LangGraph Triage & Hermes Alerts
- System Specs & Eval Harness
- ONNX Detector & Worker Loop
- Pipeline Orchestration & Modes
- Playwright Frontend Smoke Test

## God Nodes (most connected - your core abstractions)
1. `RuleEngine` - 23 edges
2. `Anomaly` - 17 edges
3. `make_engine()` - 14 edges
4. `post_frames()` - 13 edges
5. `ingest_detections()` - 12 edges
6. `post_events()` - 11 edges
7. `center_distance()` - 11 edges
8. `VideoSource` - 10 edges
9. `main()` - 10 edges
10. `_conn()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `NVIDIA Nemotron AI Agent Configuration` --references--> `build_agent_graph()`  [INFERRED]
  config.yaml → server/agent.py
- `Centroid and IoU Multi-Object Tracker` --references--> `Tracker`  [EXTRACTED]
  docs/ARCHITECTURE.md → server/tracker.py
- `VideoSource Capture Abstraction` --references--> `VideoSource`  [EXTRACTED]
  docs/ARCHITECTURE.md → edge/capture.py
- `Edge Device Streaming Configuration` --references--> `load_defaults()`  [INFERRED]
  config.yaml → edge/controller.py
- `Evaluation Video Clips Ground Truth Dataset` --references--> `ensure_labels()`  [EXTRACTED]
  data/eval_labels.yaml → scripts/eval.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Edge-to-Server Real-Time Video Ingestion and Processing Flow** — docs_architecture_edge_client, docs_api_spec_post_frames, docs_architecture_bounded_queue, docs_architecture_worker_thread, docs_architecture_onnx_detector, docs_architecture_pipeline_ingest [EXTRACTED 1.00]
- **Multi-Rule Anomaly Detection and Real-Time Alerting Engine** — docs_architecture_rule_engine, docs_anomaly_rules_rule_r1_occupancy_spike, docs_anomaly_rules_rule_r2_unexpected_object, docs_anomaly_rules_rule_r3_object_dwell, docs_architecture_alert_dispatcher [EXTRACTED 1.00]
- **Unified Ingestion Architecture across Live Video Frames and Spoofed Detections** — docs_architecture_worker_thread, docs_api_spec_post_events, docs_architecture_pipeline_ingest, docs_architecture_sqlite_wal [EXTRACTED 1.00]

## Communities (10 total, 0 thin omitted)

### Community 0 - "Edge Capture & Simulator CLI"
Cohesion: 0.09
Nodes (18): Edge Device Streaming Configuration, Edge Client Streaming Worker, VideoSource Capture Abstraction, resolve_youtube_stream_url(), VideoSource, EdgeEmitterController, load_defaults(), save_state_file() (+10 more)

### Community 1 - "FastAPI Auth & Test Suite"
Cohesion: 0.09
Nodes (38): DetectionEvent Pydantic Schema, POST /events Detection Injection Endpoint, DetectionEvent, EdgeConfigUpdate, post_edge_config(), post_events(), post_frames(), post_mode() (+30 more)

### Community 2 - "API Read Endpoints & SQLite DB"
Cohesion: 0.07
Nodes (29): GET /stats Telemetry Endpoint, POST /frames Ingestion Endpoint, FastAPI Ingestion Web Service, Database anomalies Table, Database events Table, Database frame_metrics Telemetry Table, Empirical Latency and Throughput Benchmarks, RoastGlass Web Dashboard Application (+21 more)

### Community 3 - "Tracking & Anomaly Rule Engine"
Cohesion: 0.16
Nodes (13): Anomaly, _cross_side(), _escalate_severity(), is_in_time_window(), _parse_hhmm(), point_in_polygon(), RuleEngine, box_bottom_center() (+5 more)

### Community 4 - "React RoastGlass Web Frontend"
Cohesion: 0.09
Nodes (29): dependencies, react, react-dom, devDependencies, vite, @vitejs/plugin-react, name, private (+21 more)

### Community 5 - "LangGraph Triage & Hermes Alerts"
Cohesion: 0.09
Nodes (16): NVIDIA Nemotron AI Agent Configuration, Multi-Channel Alert Dispatcher, AgentState, build_agent_graph(), decide_node(), notify_node(), suppress_node(), _default_llm_invoke() (+8 more)

### Community 6 - "System Specs & Eval Harness"
Cohesion: 0.09
Nodes (22): Home Security Configuration Profile, Public Surveillance Configuration Profile, Baseline Anomaly Rule Thresholds, Evaluation Video Clips Ground Truth Dataset, Rule R1: Occupancy Spike Detection, Rule R2: Unexpected Object Detection, Rule R3: Object Dwell Unattended Alert, Unattended Spatial Proximity and Movement Metric (+14 more)

### Community 7 - "ONNX Detector & Worker Loop"
Cohesion: 0.18
Nodes (7): lifespan(), ONNXRuntimeDetector, _annotate_frame(), _get_detector(), start_worker(), stop_worker(), _worker_loop()

### Community 8 - "Pipeline Orchestration & Modes"
Cohesion: 0.24
Nodes (9): Server Ingestion Queue and Confidence Thresholds, get_mode(), DeviceState, get_active_mode(), _get_device(), ingest_detections(), load_config(), register_frame_received() (+1 more)

### Community 9 - "Playwright Frontend Smoke Test"
Cohesion: 0.25
Nodes (3): { chromium }, fs, path

## Knowledge Gaps
- **4 isolated node(s):** `Server Ingest and Processing Entity`, `Baseline Anomaly Rule Thresholds`, `Unattended Spatial Proximity and Movement Metric`, `Empirical Latency and Throughput Benchmarks`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 63 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RoastGlass Web Dashboard Application` connect `API Read Endpoints & SQLite DB` to `React RoastGlass Web Frontend`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `RuleEngine` (e.g. with `DeviceState` and `Track`) actually correct?**
  _`RuleEngine` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Server Ingest and Processing Entity`, `Baseline Anomaly Rule Thresholds`, `Unattended Spatial Proximity and Movement Metric` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Edge Capture & Simulator CLI` be split into smaller, more focused modules?**
  _Cohesion score 0.08627450980392157 - nodes in this community are weakly interconnected._
- **Why does `POST /frames Ingestion Endpoint` connect `API Read Endpoints & SQLite DB` to `Edge Capture & Simulator CLI`, `FastAPI Auth & Test Suite`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Anomaly` (e.g. with `AgentState` and `review_anomaly()`) actually correct?**
  _`Anomaly` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `FastAPI Auth & Test Suite` be split into smaller, more focused modules?**
  _Cohesion score 0.08792270531400966 - nodes in this community are weakly interconnected._