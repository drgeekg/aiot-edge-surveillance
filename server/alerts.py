import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import time
import requests

logger = logging.getLogger(__name__)

alert_active_until: float = 0.0
last_anomaly_ts: float | None = None


def is_alert_active(now: float | None = None) -> bool:
    """Return True while the 15-second visual/overlay alert window is active."""
    t = time.time() if now is None else now
    return t < alert_active_until


def _beep() -> None:
    """Trigger a platform-appropriate local audible alert (Windows/macOS/BEL fallback)."""
    if sys.platform.startswith("win"):
        try:
            import winsound
            winsound.Beep(1000, 250)
            return
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            subprocess.Popen(
                ["afplay", "/System/Library/Sounds/Ping.aiff"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass
    sys.stdout.write("\a")
    sys.stdout.flush()


def send_hermes_webhook(
    anomaly,
    device_id: str = "",
    reason: str = "",
    webhook_url: str | None = None,
    webhook_secret: str | None = None,
) -> bool:
    """Sign an anomaly payload with HMAC-SHA256 and POST it to the Hermes webhook."""
    url = (
        webhook_url
        or os.getenv("HERMES_WEBHOOK_URL", "").strip()
        or "http://127.0.0.1:8644/webhooks/house-alert"
    )
    secret = (webhook_secret if webhook_secret is not None else os.getenv("HERMES_WEBHOOK_SECRET", "")).strip()
    # Skip delivery rather than sending unsigned webhook requests
    if not secret:
        return False

    sev = getattr(anomaly, "severity", "warning").upper()
    rule = getattr(anomaly, "rule", "anomaly")
    detail = getattr(anomaly, "detail", "")
    mode = getattr(anomaly, "mode", "public")
    zone = getattr(anomaly, "zone", "") or "global"
    ts_val = float(getattr(anomaly, "ts", time.time()))
    time_str = time.strftime("%H:%M:%S", time.localtime(ts_val if ts_val > 1e8 else time.time()))
    sev_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "INFO": "🔵"}.get(sev, "🔔")
    rule_title = rule.replace("_", " ").title()

    lines = [
        f"{sev_icon} {sev} · {rule_title}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📷 Camera : {device_id or 'edge-01'}",
        f"🛡️ Mode   : {mode.upper()} | Zone: {zone}",
        f"🕒 Time   : {time_str}",
        f"📌 Event  : {detail}",
    ]
    if reason:
        lines.append(f"🤖 Agent  : {reason}")
    msg = "\n".join(lines)

    payload_dict = {
        "event_type": rule,
        "severity": sev.lower(),
        "device_id": device_id,
        "mode": mode,
        "message": msg,
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    try:
        resp = requests.post(
            url,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": rule,
            },
            timeout=3.0,
        )
        return resp.status_code < 300
    except Exception as exc:
        logger.warning("Hermes webhook delivery failed: %s", exc)
        return False


def fire(anomaly, device_id: str = "", reason: str = "") -> None:
    """Activate the 15s alert banner, log to console, beep, and send Hermes webhook."""
    global alert_active_until, last_anomaly_ts
    now = time.time()
    alert_active_until = max(alert_active_until, now + 15.0)
    last_anomaly_ts = float(getattr(anomaly, "ts", now))

    sev = getattr(anomaly, "severity", "warning").upper()
    rule = getattr(anomaly, "rule", "anomaly")
    detail = getattr(anomaly, "detail", "")
    color = "\033[91m" if sev == "CRITICAL" else "\033[93m"
    reset = "\033[0m"
    dev_str = f" [{device_id}]" if device_id else ""
    reason_str = f" (agent: {reason})" if reason else ""
    print(f"{color}=== ALERT [{sev}]{dev_str} {rule}: {detail}{reason_str} ==={reset}", flush=True)
    _beep()
    send_hermes_webhook(anomaly, device_id=device_id, reason=reason)
