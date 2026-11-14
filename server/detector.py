import ast
from typing import Dict, List, Optional, Set
import cv2
import numpy as np
import onnxruntime as ort

COCO_NAMES: Dict[int, str] = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard",
    37: "surfboard", 38: "tennis racket", 39: "bottle", 40: "wine glass",
    41: "cup", 42: "fork", 43: "knife", 44: "spoon", 45: "bowl", 46: "banana",
    47: "apple", 48: "sandwich", 49: "orange", 50: "broccoli", 51: "carrot",
    52: "hot dog", 53: "pizza", 54: "donut", 55: "cake", 56: "chair",
    57: "couch", 58: "potted plant", 59: "bed", 60: "dining table",
    61: "toilet", 62: "tv", 63: "laptop", 64: "mouse", 65: "remote",
    66: "keyboard", 67: "cell phone", 68: "microwave", 69: "oven",
    70: "toaster", 71: "sink", 72: "refrigerator", 73: "book", 74: "clock",
    75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
    79: "toothbrush",
}


class ONNXRuntimeDetector:
    """CPU ONNX Runtime object detector for NMS-free YOLO models."""

    def __init__(
        self,
        model_path: str = "yolo26n.onnx",
        conf: float = 0.30,
        class_thresholds: Optional[Dict[str, float]] = None,
        allowed_classes: Optional[Set[str]] = None,
    ):
        """Initialize an ONNX Runtime CPU session and load class-name metadata."""
        self.model_path = model_path
        self.conf = float(conf)
        self.class_thresholds: Dict[str, float] = {
            str(k): float(v) for k, v in (class_thresholds or {}).items()
        }
        self.allowed_classes: Optional[Set[str]] = (
            set(allowed_classes) if allowed_classes else None
        )
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        meta = self.session.get_modelmeta().custom_metadata_map or {}
        if "names" in meta:
            try:
                self.names = {int(k): str(v) for k, v in ast.literal_eval(meta["names"]).items()}
            except Exception:
                self.names = COCO_NAMES
        else:
            self.names = COCO_NAMES

    def detect(
        self,
        frame_bgr: np.ndarray,
        allowed_classes: Optional[Set[str]] = None,
    ) -> List[dict]:
        """Run 640x640 letterboxed inference and return normalized detections."""
        if frame_bgr is None or frame_bgr.size == 0:
            return []
        h0, w0 = frame_bgr.shape[:2]

        # Letterbox to 640x640 with gray (114) padding
        scale = min(640.0 / w0, 640.0 / h0)
        nw, nh = int(round(w0 * scale)), int(round(h0 * scale))
        dw, dh = (640 - nw) / 2.0, (640 - nh) / 2.0

        resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )

        # BGR -> RGB, /255.0, NCHW float32
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]

        outputs = self.session.run(None, {self.input_name: blob})[0]
        rows = outputs[0]  # (300, 6): x1, y1, x2, y2, score, class_id

        active_allowed = allowed_classes if allowed_classes is not None else self.allowed_classes
        results: List[dict] = []
        for row in rows:
            score = float(row[4])
            cls_id = int(round(float(row[5])))
            cls_name = self.names.get(cls_id, str(cls_id))
            if active_allowed is not None and cls_name not in active_allowed:
                continue
            # Allow per-class lower threshold (e.g. small/distant items) without raising global cutoff
            min_conf = min(self.conf, self.class_thresholds.get(cls_name, self.conf))
            if score < min_conf:
                continue

            # Undo letterbox and normalize 0..1
            x1 = max(0.0, min(1.0, (float(row[0]) - left) / nw))
            y1 = max(0.0, min(1.0, (float(row[1]) - top) / nh))
            x2 = max(0.0, min(1.0, (float(row[2]) - left) / nw))
            y2 = max(0.0, min(1.0, (float(row[3]) - top) / nh))
            if x2 <= x1 or y2 <= y1:
                continue
            results.append(
                {
                    "class_name": cls_name,
                    "conf": round(score, 4),
                    "box": (round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)),
                }
            )
        return results
