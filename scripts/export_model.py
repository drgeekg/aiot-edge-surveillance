import os
import sys
import requests
import onnxruntime as ort

MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.onnx"
MODEL_PATH = "yolo26n.onnx"


def main():
    """Export or download NMS-free yolo26n.onnx and verify ONNX Runtime CPU tensor shapes."""
    if not os.path.exists(MODEL_PATH):
        try:
            from ultralytics import YOLO
            YOLO("yolo26n.pt").export(format="onnx", nms=False)
        except ImportError:
            print(f"Downloading pre-exported {MODEL_PATH} from {MODEL_URL}...")
            r = requests.get(MODEL_URL, timeout=60)
            r.raise_for_status()
            with open(MODEL_PATH, "wb") as f:
                f.write(r.content)

    sess = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    out = sess.get_outputs()[0]
    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"OK: {MODEL_PATH} ({size_mb:.2f} MB) | input={inp.name}:{inp.shape} | output={out.name}:{out.shape}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
