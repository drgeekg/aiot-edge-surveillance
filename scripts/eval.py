"""Evaluation harness: replay video clips through ONNXRuntimeDetector + RuleEngine and report precision/recall."""
import os
import sys
import cv2
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server.detector import ONNXRuntimeDetector
from server.rules import RuleEngine

DEFAULT_LABELS = {
    "clips": [
        {
            "path": "data/demo.mp4",
            "mode": "public",
            "expected_rules": ["unexpected_object", "object_dwell"],
        },
        {
            "path": "data/demo_attended.mp4",
            "mode": "public",
            "expected_rules": ["unexpected_object"],
            "forbidden_rules": ["object_dwell"],
        },
    ]
}


def ensure_labels(path: str = "data/eval_labels.yaml") -> dict:
    """Load evaluation clip ground-truth YAML, creating default labels if absent."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or DEFAULT_LABELS
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(DEFAULT_LABELS, f, sort_keys=False)
    return DEFAULT_LABELS


def evaluate_clip(detector: ONNXRuntimeDetector, clip_cfg: dict, base_cfg: dict, sample_fps: float = 5.0) -> set:
    """Replay one clip at sample_fps through ONNXRuntimeDetector and RuleEngine, returning fired rules."""
    path = clip_cfg["path"]
    if not os.path.exists(path):
        return set()
    cap = cv2.VideoCapture(path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(src_fps / sample_fps)))

    rules_cfg = dict(base_cfg.get("rules", {}))
    rules_cfg["mode"] = clip_cfg.get("mode", "public")
    rules_cfg["home"] = base_cfg.get("home", {})
    rules_cfg["public"] = base_cfg.get("public", {})
    engine = RuleEngine(rules_cfg)

    fired_rules = set()
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            ts = idx / float(src_fps)
            dets = detector.detect(frame)
            anomalies = engine.update(dets, ts=ts)
            for a in anomalies:
                fired_rules.add(a.rule)
        idx += 1
    cap.release()
    return fired_rules


def main() -> int:
    """Evaluate all configured clips against expected/forbidden rules and print precision/recall."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    srv = cfg.get("server", {})
    detector = ONNXRuntimeDetector(
        "yolo26n.onnx",
        conf=float(srv.get("conf_stay", 0.30)),
        class_thresholds=srv.get("class_thresholds", {}),
    )
    labels = ensure_labels()
    tp = fp = fn = 0
    for c in labels.get("clips", []):
        fired = evaluate_clip(detector, c, cfg)
        expected = set(c.get("expected_rules", []))
        forbidden = set(c.get("forbidden_rules", []))
        clip_tp = len(fired & expected)
        clip_fn = len(expected - fired)
        clip_fp = len(fired & forbidden)
        tp += clip_tp
        fn += clip_fn
        fp += clip_fp
        print(f"Clip {c['path']} [{c.get('mode','public')}]: fired={sorted(fired)} | expected={sorted(expected)}")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    print(f"Summary -> TP={tp} FP={fp} FN={fn} | Precision={precision:.2f} Recall={recall:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
