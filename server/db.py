import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

DB_PATH = "events.db"
_local = threading.local()


def _conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection configured for WAL mode and 5s busy timeout."""
    conn = getattr(_local, "conn", None)
    # Reopen connection when DB_PATH changes (e.g., temporary DBs during tests)
    if conn is None or getattr(_local, "db_path", None) != DB_PATH:
        conn = sqlite3.connect(DB_PATH, timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        _local.conn = conn
        _local.db_path = DB_PATH
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize events, anomalies, and frame_metrics SQLite tables and timestamp indexes."""
    global DB_PATH
    if db_path:
        DB_PATH = db_path
    c = _conn()
    c.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA busy_timeout=5000;

        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           REAL NOT NULL,
            device_id    TEXT NOT NULL,
            source       TEXT NOT NULL,
            object_class TEXT NOT NULL,
            count        INTEGER NOT NULL,
            avg_conf     REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS anomalies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          REAL NOT NULL,
            device_id   TEXT NOT NULL,
            rule        TEXT NOT NULL,
            detail      TEXT NOT NULL,
            severity    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS frame_metrics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           REAL NOT NULL,
            device_id    TEXT NOT NULL,
            frame_bytes  INTEGER NOT NULL,
            inference_ms REAL NOT NULL,
            e2e_ms       REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
        CREATE INDEX IF NOT EXISTS idx_anomalies_ts ON anomalies(ts);
        CREATE INDEX IF NOT EXISTS idx_metrics_ts ON frame_metrics(ts);
        """
    )
    c.commit()


def insert_event(
    ts: float,
    device_id: str,
    source: str,
    object_class: str,
    count: int,
    avg_conf: float,
) -> int:
    """Insert a debounced detection summary row into events and return its row id."""
    c = _conn()
    cur = c.execute(
        "INSERT INTO events (ts, device_id, source, object_class, count, avg_conf) VALUES (?, ?, ?, ?, ?, ?)",
        (float(ts), str(device_id), str(source), str(object_class), int(count), float(avg_conf)),
    )
    c.commit()
    return int(cur.lastrowid)


def insert_anomaly(
    ts: float,
    device_id: str,
    rule: str,
    detail: str,
    severity: str,
) -> int:
    """Insert a triggered or triage-logged anomaly row and return its row id."""
    c = _conn()
    cur = c.execute(
        "INSERT INTO anomalies (ts, device_id, rule, detail, severity) VALUES (?, ?, ?, ?, ?)",
        (float(ts), str(device_id), str(rule), str(detail), str(severity)),
    )
    c.commit()
    return int(cur.lastrowid)


def insert_frame_metric(
    ts: float,
    device_id: str,
    frame_bytes: int,
    inference_ms: float,
    e2e_ms: float,
) -> int:
    """Record per-frame payload size, ONNX inference latency, and end-to-end latency."""
    c = _conn()
    cur = c.execute(
        "INSERT INTO frame_metrics (ts, device_id, frame_bytes, inference_ms, e2e_ms) VALUES (?, ?, ?, ?, ?)",
        (float(ts), str(device_id), int(frame_bytes), float(inference_ms), float(e2e_ms)),
    )
    c.commit()
    return int(cur.lastrowid)


def recent_events(
    limit: int = 100,
    object_class: Optional[str] = None,
    device_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query newest-first detection events filtered optionally by class and device_id."""
    limit = max(1, min(int(limit), 1000))
    clauses = []
    params: List[Any] = []
    if object_class:
        clauses.append("object_class = ?")
        params.append(object_class)
    if device_id:
        clauses.append("device_id = ?")
        params.append(device_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT id, ts, source, device_id, object_class, count, avg_conf FROM events {where} ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = _conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def recent_anomalies(
    limit: int = 100,
    device_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query newest-first anomaly rows filtered optionally by device_id."""
    limit = max(1, min(int(limit), 1000))
    clauses = []
    params: List[Any] = []
    if device_id:
        clauses.append("device_id = ?")
        params.append(device_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT id, ts, device_id, rule, detail, severity FROM anomalies {where} ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = _conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def stats(now: Optional[float] = None) -> Dict[str, Any]:
    """Compute aggregate event/rule counts plus rolling 10s FPS and 60s latency averages."""
    now_ts = time.time() if now is None else float(now)
    c = _conn()
    total_events = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    anomalies_by_rule = {
        "occupancy_spike": 0,
        "unexpected_object": 0,
        "object_dwell": 0,
    }
    for row in c.execute("SELECT rule, COUNT(*) AS cnt FROM anomalies GROUP BY rule"):
        if row["rule"] in anomalies_by_rule:
            anomalies_by_rule[row["rule"]] = int(row["cnt"])

    last_anom_row = c.execute("SELECT MAX(ts) FROM anomalies").fetchone()
    last_anomaly_ts = float(last_anom_row[0]) if last_anom_row and last_anom_row[0] is not None else None

    # FPS over last 10 s of frame_metrics
    fps_cnt = c.execute(
        "SELECT COUNT(*) FROM frame_metrics WHERE ts >= ?", (now_ts - 10.0,)
    ).fetchone()[0]
    fps = round(fps_cnt / 10.0, 2) if fps_cnt > 0 else None

    # Averages over last 60 s of frame_metrics
    avg_row = c.execute(
        """
        SELECT AVG(frame_bytes) / 1024.0 AS avg_kb,
               AVG(inference_ms) AS avg_inf,
               AVG(e2e_ms) AS avg_e2e
        FROM frame_metrics
        WHERE ts >= ?
        """,
        (now_ts - 60.0,),
    ).fetchone()

    avg_frame_kb = round(float(avg_row["avg_kb"]), 2) if avg_row and avg_row["avg_kb"] is not None else None
    avg_inference_ms = round(float(avg_row["avg_inf"]), 2) if avg_row and avg_row["avg_inf"] is not None else None
    avg_e2e_ms = round(float(avg_row["avg_e2e"]), 2) if avg_row and avg_row["avg_e2e"] is not None else None

    return {
        "total_events": int(total_events),
        "anomalies_by_rule": anomalies_by_rule,
        "fps": fps,
        "avg_frame_kb": avg_frame_kb,
        "avg_inference_ms": avg_inference_ms,
        "avg_e2e_ms": avg_e2e_ms,
        "last_anomaly_ts": last_anomaly_ts,
    }
