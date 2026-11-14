import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import yaml

from server import agent, alerts, db
from server.rules import Anomaly, RuleEngine

ingest_lock = threading.Lock()


def load_config() -> dict:
    """Load config.yaml into a dictionary, returning {} when absent or empty."""
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@dataclass
class DeviceState:
    """Per-device runtime container holding RuleEngine, frame counters, and DB debounce state."""

    device_id: str
    rule_engine: RuleEngine
    last_seen: float = 0.0
    frames_received: int = 0
    source_kind: str = "api"
    last_logged_by_class: Dict[str, float] = field(default_factory=dict)

    @property
    def tracker(self):
        """Return the underlying multi-object Tracker managed by rule_engine."""
        return self.rule_engine.tracker


devices: Dict[str, DeviceState] = {}
_cfg = load_config()


def get_active_mode() -> dict:
    """Return the active deployment mode ('home'/'public') and home arming state."""
    return {
        "mode": _cfg.get("mode", "public"),
        "arming": _cfg.get("arming", "armed_night"),
    }


def set_active_mode(mode: str, arming: Optional[str] = None) -> dict:
    """Validate and apply deployment mode/arming across all active device engines."""
    mode_norm = str(mode).lower()
    if mode_norm not in ("home", "public"):
        raise ValueError("mode must be 'home' or 'public'")
    _cfg["mode"] = mode_norm
    if arming is not None:
        arm_norm = str(arming).lower()
        if arm_norm not in ("disarmed", "armed_home", "armed_night", "armed_away"):
            raise ValueError("arming must be disarmed, armed_home, armed_night, or armed_away")
        _cfg["arming"] = arm_norm
    with ingest_lock:
        for st in devices.values():
            st.rule_engine.set_mode(_cfg["mode"], _cfg.get("arming"))
    return get_active_mode()


def _get_device(device_id: str, ts: float, source_kind: str) -> DeviceState:
    """Fetch or lazily instantiate per-device state and update last-seen metadata."""
    st = devices.get(device_id)
    if st is None:
        rules_cfg = dict(_cfg.get("rules", {}))
        rules_cfg["mode"] = _cfg.get("mode", "public")
        rules_cfg["arming"] = _cfg.get("arming", "armed_night")
        rules_cfg["home"] = _cfg.get("home", {})
        rules_cfg["public"] = _cfg.get("public", {})
        st = DeviceState(
            device_id=device_id,
            rule_engine=RuleEngine(rules_cfg),
            last_seen=float(ts),
            frames_received=0,
            source_kind=source_kind,
        )
        devices[device_id] = st
    else:
        st.last_seen = max(st.last_seen, float(ts))
        if source_kind:
            st.source_kind = source_kind
    return st


def register_frame_received(device_id: str, ts: float, source_kind: str) -> DeviceState:
    """Increment frame receipt counters for device_id under ingest_lock when HTTP frame arrives."""
    with ingest_lock:
        st = _get_device(device_id, ts, source_kind)
        st.frames_received += 1
        return st


def ingest_detections(
    device_id: str,
    ts: float,
    detections: List[dict],
    source: str = "api",
    frame_bgr: Optional[np.ndarray] = None,
) -> List[Anomaly]:
    """Thread-safe unified seam for debounced event logging, rule evaluation, and alert dispatch."""
    debounce_s = float(_cfg.get("server", {}).get("debounce_seconds", 2.0))
    agent_cfg = _cfg.get("agent", {})
    # Single lock serializes worker frames and synchronous POST /events against shared device state
    with ingest_lock:
        st = _get_device(device_id, ts, source)

        # Group detections by class for debounced event logging
        grouped: Dict[str, List[dict]] = {}
        for d in detections:
            cls = d.get("class_name") or d.get("object_class")
            if not cls:
                continue
            grouped.setdefault(cls, []).append(d)

        for cls, items in grouped.items():
            last_t = st.last_logged_by_class.get(cls)
            if last_t is None or (ts - last_t) >= debounce_s:
                total_count = sum(int(i.get("count", 1)) for i in items)
                confs = [float(i.get("conf", i.get("avg_conf", 1.0))) for i in items]
                avg_conf = sum(confs) / len(confs) if confs else 1.0
                db.insert_event(
                    ts=ts,
                    device_id=device_id,
                    source=source,
                    object_class=cls,
                    count=total_count,
                    avg_conf=round(avg_conf, 4),
                )
                st.last_logged_by_class[cls] = float(ts)

        # Evaluate rules
        anomalies = st.rule_engine.update(detections, ts, frame_bgr=frame_bgr)
        for a in anomalies:
            if agent_cfg.get("enabled", False) and os.getenv("NVIDIA_API_KEY"):
                agent.submit_review(
                    anomaly=a,
                    device_id=device_id,
                    mode=st.rule_engine.mode,
                    arming=st.rule_engine.arming,
                    agent_cfg=agent_cfg,
                )
            else:
                db.insert_anomaly(
                    ts=a.ts,
                    device_id=device_id,
                    rule=a.rule,
                    detail=a.detail,
                    severity=a.severity,
                )
                alerts.fire(a, device_id=device_id)

        return anomalies
