import argparse
import os
import time
import requests


def run_simulator(server_url: str, device_id: str, real_time: bool = True) -> dict:
    """Stream a 91-second synthetic event sequence to POST /events exercising R1, R2, and R3."""
    url = f"{server_url.rstrip('/')}/events"
    api_key = os.getenv("AIIOT_API_KEY", "").strip()
    headers = {"X-API-Key": api_key} if api_key else {}
    base_ts = time.time()
    fired_counts = {"occupancy_spike": 0, "unexpected_object": 0, "object_dwell": 0}
    total_sent = 0

    print(f"Starting 90 s scenario against {url} (device_id={device_id})...")
    for sec in range(0, 91):
        ts = base_ts + float(sec)
        events = []

        if sec < 30:
            # Phase 1 (0-29 s): normal (1-2 persons, allowed objects)
            events.append({"ts": ts, "device_id": device_id, "source": "api", "object_class": "person", "count": 1 + (sec % 2), "avg_conf": 0.88})
            events.append({"ts": ts, "device_id": device_id, "source": "api", "object_class": "chair", "count": 2, "avg_conf": 0.91})
        elif sec < 60:
            # Phase 2 (30-59 s): occupancy spike (6 persons) + backpack fixed box (R2 after 5 s)
            events.append({"ts": ts, "device_id": device_id, "source": "api", "object_class": "person", "count": 6, "avg_conf": 0.85})
            events.append({"ts": ts, "device_id": device_id, "source": "api", "object_class": "backpack", "count": 1, "avg_conf": 0.82, "box": [0.20, 0.30, 0.35, 0.55]})
        else:
            # Phase 3 (60-90 s): suitcase unattended at fixed box (R3 fires at 30 s)
            events.append({"ts": ts, "device_id": device_id, "source": "api", "object_class": "suitcase", "count": 1, "avg_conf": 0.89, "box": [0.40, 0.55, 0.55, 0.85]})

        for ev in events:
            r = requests.post(url, json=ev, headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            total_sent += 1
            for a in data.get("anomalies", []):
                rule = a["rule"]
                fired_counts[rule] = fired_counts.get(rule, 0) + 1
                print(f"[t={sec:02d}s] FIRED {rule} ({a['severity']}): {a['detail']}")

        if sec % 15 == 0:
            print(f"[t={sec:02d}s] events_sent={total_sent} anomalies={fired_counts}")

        if real_time and sec < 90:
            time.sleep(1.0)

    print("=== Simulator Summary ===")
    print(f"Total events sent: {total_sent}")
    print(f"Anomalies triggered: {fired_counts}")
    return fired_counts


def main():
    """Parse CLI arguments (--server, --device-id, --fast) and execute run_simulator."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--device-id", default="sim-01")
    parser.add_argument("--fast", action="store_true", help="Skip 1s sleep between simulated seconds")
    args = parser.parse_args()
    run_simulator(args.server, args.device_id, real_time=not args.fast)


if __name__ == "__main__":
    main()
