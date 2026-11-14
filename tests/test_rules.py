import yaml
from server.rules import RuleEngine


def make_engine():
    """Instantiate a public-mode RuleEngine configured from config.yaml."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["rules"]
    return RuleEngine(cfg)


def test_ut1_occupancy_spike():
    """Verify R1 occupancy_spike stays silent at 3 persons and fires at 4 persons."""
    engine = make_engine()
    # 3 persons does not fire
    res3 = engine.update([{"class_name": "person"}] * 3, ts=0.0)
    assert [a.rule for a in res3] == []

    # 4 persons at t=0 fires R1
    engine2 = make_engine()
    res4 = engine2.update([{"class_name": "person"}] * 4, ts=0.0)
    assert [a.rule for a in res4] == ["occupancy_spike"]
    assert res4[0].severity == "warning"


def test_ut2_unexpected_object():
    """Verify R2 unexpected_object fires once a backpack remains visible for >=5 seconds."""
    engine = make_engine()
    box = (0.2, 0.2, 0.4, 0.4)
    for t in [0.0, 1.0, 2.0, 3.0, 4.0, 4.9]:
        res = engine.update([{"class_name": "backpack", "box": box}], ts=t)
        assert [a.rule for a in res] == []

    res_fire = engine.update([{"class_name": "backpack", "box": box}], ts=5.0)
    assert [a.rule for a in res_fire] == ["unexpected_object"]
    assert res_fire[0].severity == "warning"


def test_ut3_object_dwell_unattended():
    """Verify R3 object_dwell fires at critical severity after 30s unattended dwell."""
    engine = make_engine()
    box = (0.40, 0.55, 0.55, 0.85)
    fired_r3 = []
    for t in range(0, 30):
        res = engine.update([{"class_name": "suitcase", "box": box}], ts=float(t))
        fired_r3.extend(a for a in res if a.rule == "object_dwell")
    assert fired_r3 == []

    res_30 = engine.update([{"class_name": "suitcase", "box": box}], ts=30.0)
    r3_30 = [a for a in res_30 if a.rule == "object_dwell"]
    assert len(r3_30) == 1
    assert r3_30[0].severity == "critical"


def test_ut4_object_dwell_reset_by_person_near():
    """Verify owner presence/return near a tracked suitcase resets its R3 unattended timer."""
    engine = make_engine()
    bag_box = (0.40, 0.55, 0.55, 0.85)  # center (0.475, 0.70)
    person_near = (0.42, 0.50, 0.52, 0.80)  # center (0.47, 0.65), dist ~0.05 < 0.20

    for t in range(0, 31):
        dets = [{"class_name": "suitcase", "box": bag_box}]
        if t in (0, 20):
            # Owner present at t=0 when bag is placed, then owner returns at t=20 ( or stationary >=2s )
            dets.append({"class_name": "person", "box": person_near})
        elif t in (21, 22):
            dets.append({"class_name": "person", "box": person_near})
        res = engine.update(dets, ts=float(t))
        r3 = [a for a in res if a.rule == "object_dwell"]
        assert r3 == [], f"R3 should not fire at t={t}"


def test_passerby_does_not_reset_dwell_timer():
    """Verify a brief 1-second non-owner passerby does not reset the R3 unattended timer."""
    engine = make_engine()
    bag_box = (0.40, 0.55, 0.55, 0.85)
    passerby_box = (0.42, 0.50, 0.52, 0.80)

    fired_r3 = []
    for t in range(0, 31):
        dets = [{"class_name": "suitcase", "box": bag_box}]
        # Brief 1-second passerby at t=15 who was not the owner at t=0
        if t == 15:
            dets.append({"class_name": "person", "box": passerby_box})
        res = engine.update(dets, ts=float(t))
        fired_r3.extend(a for a in res if a.rule == "object_dwell")

    assert len(fired_r3) == 1
    assert fired_r3[0].ts == 30.0


def test_nudge_without_person_does_not_reset_dwell_timer():
    """Verify bag jitter without a nearby person does not reset unattended dwell timing."""
    engine = make_engine()
    box1 = (0.40, 0.55, 0.55, 0.85)
    # Shifted slightly so IoU with box1 < 0.3, but center_distance <= 0.25 so it matches the track
    box2 = (0.52, 0.55, 0.67, 0.85)

    fired_r3 = []
    for t in range(0, 31):
        b = box1 if t < 15 else box2
        res = engine.update([{"class_name": "suitcase", "box": b}], ts=float(t))
        fired_r3.extend(a for a in res if a.rule == "object_dwell")

    assert len(fired_r3) == 1
    assert fired_r3[0].ts == 30.0


def test_bag_occluded_for_4s_keeps_track_and_fires():
    """Verify a 4-second detection dropout preserves track continuity under 15s timeout."""
    engine = make_engine()
    bag_box = (0.40, 0.55, 0.55, 0.85)

    fired_r3 = []
    for t in range(0, 31):
        # Hidden for 4 seconds (t=10, 11, 12, 13)
        dets = [] if 10 <= t <= 13 else [{"class_name": "suitcase", "box": bag_box}]
        res = engine.update(dets, ts=float(t))
        fired_r3.extend(a for a in res if a.rule == "object_dwell")

    assert len(fired_r3) == 1
    assert fired_r3[0].ts == 30.0


def test_two_bags_independent_cooldown():
    """Verify two separate watch-class bags enforce cooldowns independently by track_id."""
    engine = make_engine()
    bag_a = (0.10, 0.10, 0.25, 0.25)
    bag_b = (0.70, 0.70, 0.85, 0.85)

    r2_fires = []
    for t in range(0, 8):
        dets = [{"class_name": "backpack", "box": bag_a}]
        if t >= 2:
            dets.append({"class_name": "backpack", "box": bag_b})
        res = engine.update(dets, ts=float(t))
        r2_fires.extend((t, a) for a in res if a.rule == "unexpected_object")

    # Bag A fires at t=5, Bag B (placed at t=2) must fire at t=7 despite 10s rule cooldown
    fire_times = [t for t, _ in r2_fires]
    assert 5 in fire_times
    assert 7 in fire_times


def test_confidence_hysteresis():
    """Verify conf_enter (0.40) and conf_stay (0.30) hysteresis keeps existing tracks alive."""
    engine = make_engine()
    bag_box = (0.20, 0.20, 0.35, 0.35)

    # Below 0.40 does not start a track
    engine.update([{"class_name": "backpack", "box": bag_box, "conf": 0.35}], ts=0.0)
    assert len(engine.tracker.tracks.get("backpack", [])) == 0

    # At 0.42 starts a track, and stays alive at 0.32 for 5s -> fires R2
    engine.update([{"class_name": "backpack", "box": bag_box, "conf": 0.42}], ts=1.0)
    assert len(engine.tracker.tracks.get("backpack", [])) == 1
    for t in [2.0, 3.0, 4.0, 5.0]:
        res = engine.update([{"class_name": "backpack", "box": bag_box, "conf": 0.32}], ts=t)
    res_6 = engine.update([{"class_name": "backpack", "box": bag_box, "conf": 0.32}], ts=6.0)
    assert [a.rule for a in res_6] == ["unexpected_object"]


def test_ut5_cooldown():
    """Verify repeated rule triggers respect the 10-second per-key cooldown window."""
    engine = make_engine()
    fire_times = []
    for t in range(0, 26):
        res = engine.update([{"class_name": "person"}] * 4, ts=float(t))
        if any(a.rule == "occupancy_spike" for a in res):
            fire_times.append(float(t))

    assert len(fire_times) >= 2
    assert fire_times[0] == 0.0
    for i in range(1, len(fire_times)):
        assert fire_times[i] - fire_times[i - 1] >= 10.0


def test_api_frames_and_events(tmp_path):
    """Verify /frames validation, /events ingestion, and /health 200/503 worker/model checks."""
    import asyncio
    import pytest
    from fastapi import HTTPException, Request
    from server import app as server_app, db

    db.init_db(str(tmp_path / "test_events.db"))

    def make_req(payload: bytes) -> Request:
        """Build a minimal ASGI Request holding payload bytes."""
        async def receive():
            """Yield a single http.request ASGI message with payload."""
            return {"type": "http.request", "body": payload, "more_body": False}
        return Request({"type": "http", "method": "POST", "path": "/frames", "headers": []}, receive)

    # TC-06: 400 on non-JPEG, 413 on >2MB, 202 on valid JPEG
    with pytest.raises(HTTPException) as exc400:
        asyncio.run(server_app.post_frames(make_req(b"not-a-jpeg"), device_id="ut-edge", ts=100.0, seq=1, source_kind="file"))
    assert exc400.value.status_code == 400

    with pytest.raises(HTTPException) as exc413:
        asyncio.run(server_app.post_frames(make_req(b"\xff\xd8" + b"0" * (2 * 1024 * 1024 + 5)), device_id="ut-edge", ts=100.0, seq=2, source_kind="file"))
    assert exc413.value.status_code == 413

    r202 = asyncio.run(server_app.post_frames(make_req(b"\xff\xd8\xff\xd9"), device_id="ut-edge", ts=100.0, seq=3, source_kind="file"))
    assert r202["status"] == "queued"

    # TC-07 & TC-08: POST /events + GET /stats & /health
    r_ev = server_app.post_events(server_app.DetectionEvent(ts=200.0, device_id="ut-sim", object_class="person", count=5, avg_conf=0.9))
    assert r_ev["status"] == "logged"
    assert r_ev["anomalies"][0]["rule"] == "occupancy_spike"

    from server import worker
    worker.stop_worker()
    with pytest.raises(HTTPException) as exc503_stopped:
        server_app.get_health()
    assert exc503_stopped.value.status_code == 503
    assert exc503_stopped.value.detail["worker"] == "stopped"

    worker.start_worker()
    try:
        assert server_app.get_health()["status"] == "ok"
        orig_exists = server_app.os.path.exists
        server_app.os.path.exists = lambda p: False if p == "yolo26n.onnx" else orig_exists(p)
        try:
            with pytest.raises(HTTPException) as exc503_no_model:
                server_app.get_health()
            assert exc503_no_model.value.status_code == 503
            assert exc503_no_model.value.detail["model_exists"] is False
        finally:
            server_app.os.path.exists = orig_exists
    finally:
        worker.stop_worker()


def _make_sec_req(
    payload: bytes = b"\xff\xd8\xff\xd9",
    headers: list | None = None,
    server_host: str = "127.0.0.1",
    body_called: list | None = None,
):
    """Build a synthetic ASGI Request with configurable headers, host, and read-tracking hook."""
    from fastapi import Request

    hdrs = headers or []

    async def receive():
        """Record body read invocation and return payload bytes."""
        if body_called is not None:
            body_called.append(True)
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/frames",
        "headers": hdrs,
        "server": (server_host, 8000),
        "client": ("127.0.0.1", 50000),
    }
    return Request(scope, receive)


def test_security_401_missing_api_key(monkeypatch):
    """Verify 401 when X-API-Key is missing or bound to 0.0.0.0 without AIIOT_API_KEY."""
    import asyncio
    import pytest
    from fastapi import HTTPException
    from server import app as server_app

    monkeypatch.setenv("AIIOT_API_KEY", "test")
    with pytest.raises(HTTPException) as exc_frames:
        asyncio.run(server_app.post_frames(_make_sec_req(), device_id="ut-sec", ts=1.0, seq=1, source_kind="file"))
    assert exc_frames.value.status_code == 401

    with pytest.raises(HTTPException) as exc_events:
        server_app.post_events(
            server_app.DetectionEvent(ts=1.0, object_class="person", count=1),
            request=_make_sec_req(),
        )
    assert exc_events.value.status_code == 401

    with pytest.raises(HTTPException) as exc_cfg:
        server_app.post_edge_config(
            server_app.EdgeConfigUpdate(fps=5.0),
            request=_make_sec_req(),
        )
    assert exc_cfg.value.status_code == 401

    # Also 401 when bound to 0.0.0.0 without key
    monkeypatch.delenv("AIIOT_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_0000:
        asyncio.run(
            server_app.post_frames(
                _make_sec_req(server_host="0.0.0.0"),
                device_id="ut-sec",
                ts=1.0,
                seq=2,
                source_kind="file",
            )
        )
    assert exc_0000.value.status_code == 401


def test_security_403_invalid_api_key(monkeypatch):
    """Verify 403 Forbidden when an incorrect X-API-Key header is supplied."""
    import asyncio
    import pytest
    from fastapi import HTTPException
    from server import app as server_app

    monkeypatch.setenv("AIIOT_API_KEY", "test")
    bad_req = _make_sec_req(headers=[(b"x-api-key", b"wrong-key")])
    with pytest.raises(HTTPException) as exc_403:
        asyncio.run(server_app.post_frames(bad_req, device_id="ut-sec", ts=1.0, seq=1, source_kind="file"))
    assert exc_403.value.status_code == 403

    with pytest.raises(HTTPException) as exc_ev_403:
        server_app.post_events(
            server_app.DetectionEvent(ts=1.0, object_class="person", count=1),
            request=bad_req,
        )
    assert exc_ev_403.value.status_code == 403


def test_security_413_content_length_before_read(monkeypatch):
    """Verify oversized Content-Length requests are rejected with 413 before body reads."""
    import asyncio
    import pytest
    from fastapi import HTTPException
    from server import app as server_app

    monkeypatch.delenv("AIIOT_API_KEY", raising=False)
    body_read_tracker = []
    cl_req = _make_sec_req(
        payload=b"\xff\xd8\xff\xd9",
        headers=[(b"content-length", str(3 * 1024 * 1024).encode())],
        body_called=body_read_tracker,
    )
    with pytest.raises(HTTPException) as exc_cl:
        asyncio.run(server_app.post_frames(cl_req, device_id="ut-sec", ts=1.0, seq=3, source_kind="file"))
    assert exc_cl.value.status_code == 413
    assert body_read_tracker == [], "Body must not be read when Content-Length > 2 MB"


def test_security_400_oversize_jpeg_dimensions(monkeypatch):
    """Verify JPEG headers claiming dimensions >4096px are rejected with 400."""
    import asyncio
    import struct
    import pytest
    from fastapi import HTTPException
    from server import app as server_app

    monkeypatch.delenv("AIIOT_API_KEY", raising=False)
    sof0_seg = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, 5000, 5000, 1) + b"\x01\x11\x00"
    oversized_jpeg = b"\xff\xd8" + sof0_seg + b"\xff\xd9"
    with pytest.raises(HTTPException) as exc_dim:
        asyncio.run(
            server_app.post_frames(
                _make_sec_req(payload=oversized_jpeg),
                device_id="ut-sec",
                ts=1.0,
                seq=4,
                source_kind="file",
            )
        )
    assert exc_dim.value.status_code == 400
    assert "4096" in exc_dim.value.detail


def test_security_422_edge_config_bounds():
    """Verify EdgeConfigUpdate enforces Pydantic bounds on fps, width, and quality."""
    import pytest
    from pydantic import ValidationError
    from server import app as server_app

    for bad_kwargs in [
        {"fps": 0.1},
        {"fps": 60.0},
        {"width": 80},
        {"width": 3840},
        {"quality": 5},
        {"quality": 105},
    ]:
        with pytest.raises(ValidationError):
            server_app.EdgeConfigUpdate(**bad_kwargs)


def test_security_422_bad_source():
    """Verify EdgeConfigUpdate blocks traversal/disallowed schemes while allowing safe sources."""
    import pytest
    from pydantic import ValidationError
    from server import app as server_app

    for bad_src in ["../secret.mp4", "C:/Windows/System32/cmd.exe", "file:///etc/passwd"]:
        with pytest.raises(ValidationError):
            server_app.EdgeConfigUpdate(source=bad_src)

    assert server_app.EdgeConfigUpdate(source="data/demo.mp4").source == "data/demo.mp4"
    assert server_app.EdgeConfigUpdate(source="0").source == "0"
    assert server_app.EdgeConfigUpdate(source="rtsp://192.168.1.10/live").source == "rtsp://192.168.1.10/live"


def test_security_cors_restricted():
    """Verify CORS allowlist permits only local Vite frontend origins."""
    from server import app as server_app

    assert server_app.ALLOWED_CORS_ORIGINS == [
        "http://localhost:5173",
        "http://localhost:5174",
    ]


def test_api_key_set_accepted_and_sent_by_clients(monkeypatch):
    """Verify valid X-API-Key requests succeed and simulator.py forwards X-API-Key."""
    import asyncio
    from server import app as server_app
    from scripts import simulator

    monkeypatch.setenv("AIIOT_API_KEY", "test")
    ok_req = _make_sec_req(headers=[(b"x-api-key", b"test")])
    r_ok = asyncio.run(server_app.post_frames(ok_req, device_id="ut-sec", ts=1.0, seq=1, source_kind="file"))
    assert r_ok["status"] == "queued"

    r_ev = server_app.post_events(
        server_app.DetectionEvent(ts=1.0, object_class="person", count=1),
        request=ok_req,
    )
    assert r_ev["status"] == "logged"

    # Verify simulator sends X-API-Key: test
    captured_headers = []

    class DummyResp:
        """Minimal fake requests response stub."""

        def raise_for_status(self):
            """No-op status check stub."""
            pass

        def json(self):
            """Return empty anomalies payload."""
            return {"anomalies": []}

    def fake_post(url, json=None, headers=None, timeout=5):
        """Capture outbound request headers and halt simulator loop."""
        captured_headers.append(headers)
        raise StopIteration()

    monkeypatch.setattr(simulator.requests, "post", fake_post)
    try:
        simulator.run_simulator("http://localhost:8000", "sim-test", real_time=False)
    except StopIteration:
        pass
    assert captured_headers == [{"X-API-Key": "test"}]


def make_home_engine(arming: str = "armed_night"):
    """Instantiate a home-mode RuleEngine configured from config.yaml."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        full_cfg = yaml.safe_load(f)
    rcfg = dict(full_cfg["rules"])
    rcfg["mode"] = "home"
    rcfg["arming"] = arming
    rcfg["home"] = full_cfg["home"]
    rcfg["public"] = full_cfg["public"]
    return RuleEngine(rcfg)


def test_home_rules_zone_loiter_night_and_pets():
    """Verify home-mode pet immunity, night_person, person_in_zone, and critical loitering."""
    eng = make_home_engine("armed_night")
    # Pet (dog) in door zone does not trigger person rules
    dog_box = (0.20, 0.50, 0.35, 0.80)
    assert eng.update([{"class_name": "dog", "box": dog_box}], ts=0.0) == []

    # Person in door zone: night_person at t=0, person_in_zone at t=2, loitering at t=20
    p_box = (0.25, 0.45, 0.40, 0.90)  # bottom center (0.325, 0.90) inside door polygon
    r0 = eng.update([{"class_name": "person", "box": p_box}], ts=0.0)
    assert "night_person" in [a.rule for a in r0]

    r2 = eng.update([{"class_name": "person", "box": p_box}], ts=2.5)
    assert "person_in_zone" in [a.rule for a in r2]

    eng.update([{"class_name": "person", "box": p_box}], ts=12.0)
    r20 = eng.update([{"class_name": "person", "box": p_box}], ts=21.0)
    loit = [a for a in r20 if a.rule == "loitering"]
    assert len(loit) == 1 and loit[0].severity == "critical"


def test_home_package_left_taken_and_person_down():
    """Verify object_left_at_door, object_taken_from_door, and horizontal person_down rules."""
    eng = make_home_engine("armed_away")
    pkg_box = (0.25, 0.60, 0.35, 0.80)  # inside door zone
    eng.update([{"class_name": "suitcase", "box": pkg_box}], ts=0.0)
    r_left = eng.update([{"class_name": "suitcase", "box": pkg_box}], ts=11.0)
    assert "object_left_at_door" in [a.rule for a in r_left]

    # Person arrives at t=12 and package disappears by t=16 -> object_taken_from_door
    p_box = (0.22, 0.40, 0.38, 0.85)
    eng.update([{"class_name": "suitcase", "box": pkg_box}, {"class_name": "person", "box": p_box}], ts=12.0)
    r_taken = eng.update([{"class_name": "person", "box": p_box}], ts=16.0)
    assert "object_taken_from_door" in [a.rule for a in r_taken]

    # Person down (wide aspect ratio w/h >= 1.2 for >= 10s)
    eng2 = make_home_engine("armed_home")
    down_box = (0.20, 0.60, 0.70, 0.80)  # w=0.50, h=0.20 -> ratio=2.5
    eng2.update([{"class_name": "person", "box": down_box}], ts=0.0)
    r_down = eng2.update([{"class_name": "person", "box": down_box}], ts=11.0)
    assert "person_down" in [a.rule for a in r_down]


def test_public_extended_rules_dispersal_and_zones():
    """Verify public-mode sudden_dispersal and vehicle_in_pedestrian_zone triggers."""
    eng = make_engine()
    with open("config.yaml", "r", encoding="utf-8") as f:
        full_cfg = yaml.safe_load(f)
    eng.public_cfg = full_cfg["public"]

    # 6 persons at t=1, then drops to 1 at t=3 -> sudden_dispersal
    eng.update([{"class_name": "person"}] * 6, ts=1.0)
    r_disp = eng.update([{"class_name": "person"}] * 1, ts=3.0)
    assert "sudden_dispersal" in [a.rule for a in r_disp]

    # Vehicle in pedestrian zone
    r_veh = eng.update(
        [{"class_name": "car", "box": (0.30, 0.50, 0.50, 0.80), "zone_test": True}],
        ts=5.0,
    )
    assert "vehicle_in_pedestrian_zone" in [a.rule for a in r_veh]


def test_camera_tamper_and_escalation():
    """Verify S2 camera_tamper_blocked on dark frames and S5 repeat_escalation to critical."""
    import numpy as np

    eng = make_engine()
    eng.cooldown_seconds = 1.0
    dark_frame = np.zeros((120, 160, 3), dtype=np.uint8)
    eng.update([], ts=0.0, frame_bgr=dark_frame)
    r_tamper = eng.update([], ts=6.0, frame_bgr=dark_frame)
    assert "camera_tamper_blocked" in [a.rule for a in r_tamper]

    # Repeat escalation: 3rd occupancy_spike escalates warning -> critical
    for t in (10.0, 12.0):
        eng.update([{"class_name": "person"}] * 5, ts=t)
    r_esc = eng.update([{"class_name": "person"}] * 5, ts=14.0)
    occ = [a for a in r_esc if a.rule == "occupancy_spike"]
    assert len(occ) == 1 and occ[0].severity == "critical"


def test_langgraph_agent_triage_and_fail_open(tmp_path, monkeypatch):
    """Verify LangGraph confirm/upgrade, suppression, and fail-open behavior on LLM errors."""
    from server import agent, alerts, db
    from server.rules import Anomaly

    db.init_db(str(tmp_path / "agent_test.db"))
    fired = []
    monkeypatch.setattr(alerts, "fire", lambda a, device_id="", reason="": fired.append((a.rule, a.severity, reason)))

    anom = Anomaly(rule="person_in_zone", detail="Person in door", severity="warning", ts=100.0, policy="review", mode="home")

    # 1. Agent confirms real and upgrades severity
    res_real = agent.review_anomaly(
        anom,
        device_id="ut-cam",
        mode="home",
        agent_cfg={"enabled": True},
        llm_fn=lambda prompt, cfg: '{"real": true, "severity": "critical", "reason": "night intrusion"}',
    )
    assert res_real["action"] == "notified"
    assert fired[-1] == ("person_in_zone", "critical", "night intrusion")

    # 2. Agent suppresses false alarm
    anom2 = Anomaly(rule="loitering", detail="Brief shadow", severity="warning", ts=110.0, policy="review", mode="home")
    res_sup = agent.review_anomaly(
        anom2,
        device_id="ut-cam",
        mode="home",
        agent_cfg={"enabled": True},
        llm_fn=lambda prompt, cfg: '{"real": false, "severity": "info", "reason": "likely shadow"}',
    )
    assert res_sup["action"] == "suppressed"
    assert len(fired) == 1

    # 3. LLM error -> fail-open (still notifies!)
    anom3 = Anomaly(rule="night_person", detail="Person at night", severity="warning", ts=120.0, policy="review", mode="home")

    def broken_llm(prompt, cfg):
        """Simulate an upstream LLM outage."""
        raise RuntimeError("API down")

    res_err = agent.review_anomaly(
        anom3,
        device_id="ut-cam",
        mode="home",
        agent_cfg={"enabled": True},
        llm_fn=broken_llm,
    )
    assert res_err["action"] == "notified"
    assert len(fired) == 2
    assert "fail-open" in fired[-1][2]


def test_hermes_webhook_signing(monkeypatch):
    """Verify send_hermes_webhook attaches HMAC-SHA256 X-Hub-Signature-256 header."""
    from server import alerts
    from server.rules import Anomaly

    sent = {}

    class Resp:
        """Fake HTTP 200 response stub."""

        status_code = 200

    def fake_post(url, data=None, headers=None, timeout=3.0):
        """Capture outgoing webhook POST arguments for signature assertions."""
        sent["url"] = url
        sent["data"] = data
        sent["headers"] = headers
        return Resp()

    monkeypatch.setattr(alerts.requests, "post", fake_post)
    a = Anomaly(rule="person_in_zone", detail="Person in door", severity="critical", ts=1.0, mode="home")
    ok = alerts.send_hermes_webhook(
        a,
        device_id="edge-01",
        reason="confirmed",
        webhook_url="http://127.0.0.1:8644/webhooks/house-alert",
        webhook_secret="test-secret",
    )
    assert ok is True
    assert sent["headers"]["X-Hub-Signature-256"].startswith("sha256=")




