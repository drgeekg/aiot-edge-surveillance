# DATABASE.md - SQLite (events.db)

## Schema

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,              -- epoch seconds (edge capture time)
    device_id    TEXT NOT NULL,              -- e.g. 'edge-01', 'sim-01'
    source       TEXT NOT NULL,              -- 'live' | 'file' | 'url' | 'api'
    object_class TEXT NOT NULL,              -- COCO class name
    count        INTEGER NOT NULL,
    avg_conf     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    device_id   TEXT NOT NULL,
    rule        TEXT NOT NULL,               -- occupancy_spike | unexpected_object | object_dwell
    detail      TEXT NOT NULL,
    severity    TEXT NOT NULL                -- 'info'|'warning'|'critical'
);

CREATE TABLE IF NOT EXISTS frame_metrics (   -- evidence for the edge-vs-server report
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,              -- edge capture time
    device_id    TEXT NOT NULL,
    frame_bytes  INTEGER NOT NULL,           -- JPEG size received
    inference_ms REAL NOT NULL,              -- detector time on the server
    e2e_ms       REAL NOT NULL               -- server finish time - capture ts
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_anomalies_ts ON anomalies(ts);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON frame_metrics(ts);
```

## Access
- stdlib `sqlite3` only (no ORM), all queries parameterized, one connection per thread.
- Write paths: `ingest_detections()` (events, anomalies) and the worker
  (`frame_metrics`), all inside the server process; writes to events and
  anomalies are serialized by `ingest_lock`.
- Read paths: API handlers. The dashboard reads through the API, not the DB file.
- WAL mode lets API reads proceed while the worker writes.

## Verify manually
```bash
sqlite3 events.db "SELECT COUNT(*) FROM events;"
sqlite3 events.db "SELECT rule, detail, severity FROM anomalies ORDER BY ts DESC LIMIT 5;"
sqlite3 events.db "SELECT ROUND(AVG(frame_bytes)/1024.0,1) AS avg_kb, ROUND(AVG(inference_ms),1) AS avg_inf_ms, ROUND(AVG(e2e_ms),1) AS avg_e2e_ms FROM frame_metrics;"
```

## Retention
MVP: none (demo volumes are small; `frame_metrics` grows by about 5 rows per
second per device, ~18k rows/hour). Note for report: "retention/rotation would
be a scheduled DELETE on a real deployment."
