# TEST_PLAN.md

## Acceptance Criteria (definition of done)
- [x] AC-1 `edge_client.py` streams `demo.mp4` to the server for ≥ 5 min with no crash on either side; restarting the server mid-run makes the edge reconnect
- [x] AC-2 All 3 rules fire on streamed footage and rows exist in `anomalies`
- [x] AC-3 Simulator alone (no camera, no detector) reproduces all 3 anomalies via `POST /events`
- [x] AC-4 Dashboard shows the annotated live frame, tables and chart during a stream run
- [x] AC-5 `/health`, `/docs`, `/stats`, `/devices` respond; `/stats` consistent with DB counts
- [x] AC-6 ≥ 90 s demo video showing both the edge and server terminals + ≥ 5 screenshots (DB CLI, /docs, dashboard, alert frame, boxes frame)
- [x] AC-7 README complete with architecture diagram + hardware/architecture statement
- [x] AC-8 Report table of edge-vs-server cost from `frame_metrics`: KB/frame, KB/s, inference ms, e2e ms, plus CPU model
- [x] AC-9 `pytest tests/` passes

## Unit tests (`tests/test_rules.py`, fake timestamps, no I/O)
| UT | Setup | Expected |
|---|---|---|
| UT-1 | 4 persons at t=0 | R1 fires; 3 persons does not |
| UT-2 | `backpack` present t=0..4.9 then t=5.0 | R2 fires at 5.0, not before |
| UT-3 | `suitcase` fixed box, no persons, t=0..30 | R3 fires at 30 s |
| UT-4 | Same, but a person box within `owner_radius` at t=20 | R3 does not fire at 30 s (clock reset) |
| UT-5 | Anomaly condition held for 25 s | Same rule fires once, then ≥ 10 s gap |

## Manual Test Cases

| TC | Steps | Expected |
|---|---|---|
| TC-01 Webcam edge | Server + `edge_client.py --source 0` | Frames accepted, `/frames/latest` shows boxes, FPS ≥ 5 in `/stats` |
| TC-02 File edge | `--source data/demo.mp4` | Loops, detections stable, processed FPS ≥ 8 capacity (else set `process_every_n_frames: 2`) |
| TC-03 R1 fire | Simulator phase 2 or crowd frame via edge | `occupancy_spike` row + banner + beep |
| TC-04 R2 fire | `backpack` for ≥ 5 s | `unexpected_object` warning |
| TC-05 R3 fire / no-fire | Bag left 30 s with nobody near; repeat with a person standing next to it | `object_dwell` critical in the first case; none in the second |
| TC-06 Frame ingest | curl `POST /frames` (see API_SPEC.md) | `202` with queue depth; bad body → `400`; > 2 MB → `413` |
| TC-07 Event injection | curl `POST /events` | `200` + anomaly echoed when a rule triggers |
| TC-08 Query endpoints | `GET /events /anomalies /stats /devices` | Newest-first lists; stats match DB |
| TC-09 Dashboard | Streamlit + edge (or simulator) running | Frame, tables, chart refresh every 2 s; banner within 15 s of an anomaly |
| TC-10 Cooldown | Hold an anomaly condition for 30 s | Same rule fires once, then ≥ 10 s gap |
| TC-11 Server restart | Kill and restart uvicorn while the edge runs | Edge logs errors, backs off, resumes; no crash |
| TC-12 Backpressure | Run edge at `--fps 15` or set `process_every_n_frames: 4` | Queue depth stays ≤ 8, `frames_dropped` rises, memory stays flat |
| TC-13 Two devices | Edge on a second device via `--server http://<laptop-ip>:8000` | Same behavior as TC-02 |
| TC-14 Beep | Trigger any anomaly on your OS | Audible beep (otherwise fix `alerts.py` backend) |

## Performance Check
Record over 60 s on the demo machine: processed FPS, average inference ms,
KB per frame, KB/s, e2e latency (same host), and the CPU model. Put the numbers
in the report and compare against streaming raw frames and against sending only
JSON events. If processed FPS < 5: lower `edge.fps`/`edge.width` or set
`process_every_n_frames: 2` and re-measure.

### Recorded Results (`12th Gen Intel(R) Core(TM) i5-12500H`, 457 frames over >60 s)
- **Processed FPS**: 5.0 FPS (streamed) / ~36.2 FPS single-thread server capacity
- **Average Inference (`inference_ms`)**: `27.6 ms`
- **Average Frame Size (`frame_bytes`)**: `31.0 KB` (`23.3 KB` on `demo.mp4`) vs. `900.0 KB` raw BGR
- **Bandwidth (`KB/s` @ 5 FPS)**: `116.5 – 155.0 KB/s` (vs. `4,500 KB/s` raw BGR; `~0.9 KB/s` for JSON-only `POST /events`)
- **Average End-to-End Latency (`e2e_ms`, same host)**: `50.5 – 67.0 ms`
