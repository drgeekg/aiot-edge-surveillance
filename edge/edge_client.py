import argparse
import json
import os
import sys
import time
import cv2
import requests
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from edge.capture import VideoSource

STATE_PATH = os.path.join("data", "edge_state.json")


def load_edge_defaults() -> dict:
    """Read default edge capture settings from config.yaml if available."""
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("edge", {})
    return {}


def read_runtime_state() -> dict | None:
    """Safely read runtime control overrides from data/edge_state.json."""
    if not os.path.exists(STATE_PATH):
        return None
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    """Run the standalone edge CLI loop that captures, resizes, encodes, and uploads JPEGs."""
    defaults = load_edge_defaults()
    parser = argparse.ArgumentParser(description="Edge frame capture and HTTP streamer")
    parser.add_argument("--source", default="0", help="Webcam index, video file path, or URL")
    parser.add_argument("--server", default="http://localhost:8000", help="Server base URL")
    parser.add_argument("--device-id", default=defaults.get("device_id", "edge-01"))
    parser.add_argument("--fps", type=float, default=float(defaults.get("fps", 5)))
    parser.add_argument("--width", type=int, default=int(defaults.get("width", 640)))
    parser.add_argument("--quality", type=int, default=int(defaults.get("jpeg_quality", 70)))
    parser.add_argument("--duration", type=float, default=0.0, help="Optional run duration in seconds (0 = infinite)")
    args = parser.parse_args()

    current_source = str(args.source)
    try:
        vs = VideoSource(current_source)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    fps = float(args.fps)
    width = int(args.width)
    quality = int(args.quality)
    device_id = str(args.device_id)
    endpoint = f"{args.server.rstrip('/')}/frames"
    seq = 0
    backoff = 0.5
    last_send = 0.0
    stat_start = time.time()
    run_start = stat_start
    sent_in_window = 0
    bytes_in_window = 0
    last_q_depth = 0
    last_state_check = 0.0
    session = requests.Session()

    print(
        f"Edge node '{device_id}' streaming '{current_source}' ({vs.source_kind}) -> {endpoint} "
        f"at {fps} FPS, width={width}, quality={quality}"
    )

    try:
        while True:
            now = time.time()
            if args.duration > 0 and (now - run_start) >= args.duration:
                break

            # Hot-reload video source & encoder settings from Edge Control Dashboard if updated
            if (now - last_state_check) >= 0.4:
                last_state_check = now
                st_cfg = read_runtime_state()
                if st_cfg:
                    if not st_cfg.get("streaming", True):
                        time.sleep(0.2)
                        continue
                    new_src = str(st_cfg.get("source", current_source))
                    if new_src and new_src != current_source:
                        try:
                            new_vs = VideoSource(new_src)
                            vs.release()
                            vs = new_vs
                            current_source = new_src
                            print(f"[edge] Hot-swapped video source -> '{current_source}' ({vs.source_kind})", flush=True)
                        except Exception as e:
                            print(f"[edge] Source swap failed for '{new_src}': {e}", flush=True)
                    fps = float(st_cfg.get("fps", fps))
                    width = int(st_cfg.get("width", width))
                    quality = int(st_cfg.get("quality", quality))
                    device_id = str(st_cfg.get("device_id", device_id))

            interval = 1.0 / max(0.1, fps)
            frame = vs.read()
            if frame is None:
                time.sleep(0.05)
                continue

            now = time.time()
            if (now - last_send) < interval:
                time.sleep(max(0.005, min(0.05, interval - (now - last_send))))
                continue

            h, w = frame.shape[:2]
            if w != width and w > 0:
                new_h = max(1, int(round(h * (width / float(w)))))
                frame = cv2.resize(frame, (width, new_h), interpolation=cv2.INTER_AREA)

            ok, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
            if not ok:
                continue
            jpeg_bytes = enc.tobytes()

            seq += 1
            capture_ts = time.time()
            last_send = capture_ts

            try:
                api_key = os.getenv("AIIOT_API_KEY", "").strip()
                hdrs = {"Content-Type": "image/jpeg"}
                if api_key:
                    hdrs["X-API-Key"] = api_key
                resp = session.post(
                    endpoint,
                    params={
                        "device_id": device_id,
                        "ts": f"{capture_ts:.4f}",
                        "seq": seq,
                        "source_kind": vs.source_kind,
                    },
                    data=jpeg_bytes,
                    headers=hdrs,
                    timeout=2.0,
                )
                resp.raise_for_status()
                data = resp.json()
                last_q_depth = data.get("queue_depth", 0)
                sent_in_window += 1
                bytes_in_window += len(jpeg_bytes)
                backoff = 0.5
            except Exception as e:
                print(f"[edge] POST /frames error: {e} — backing off {backoff:.1f}s", flush=True)
                time.sleep(backoff)
                backoff = min(5.0, backoff * 2.0)
                continue

            elapsed = time.time() - stat_start
            if elapsed >= 5.0:
                kbps = (bytes_in_window / 1024.0) / elapsed
                print(
                    f"[edge] frames_sent={seq} | window_fps={sent_in_window/elapsed:.1f} | "
                    f"rate={kbps:.1f} KB/s | server_queue_depth={last_q_depth}",
                    flush=True,
                )
                stat_start = time.time()
                sent_in_window = 0
                bytes_in_window = 0
    finally:
        vs.release()


if __name__ == "__main__":
    main()
