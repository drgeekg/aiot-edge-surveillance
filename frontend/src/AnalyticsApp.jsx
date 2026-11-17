import React, { useEffect, useMemo, useState } from 'react';
import {
  API_BASE,
  ConsolePageHeader,
  ConsoleTopBar,
  MetricStrip,
  TabBar,
  buildHeaders,
  formatClock,
  formatDuration,
} from './components/ConsoleShell';

const POLL_TELEMETRY_MS = 650;
const POLL_FRAME_MS = 260;
const ACTIVE_ALERT_WINDOW_S = 15;
const R1_PERSON_THRESHOLD = 3;

const RULE_LABELS = {
  occupancy_spike: 'R1 · Occupancy spike',
  unexpected_object: 'R2 · Unexpected object',
  object_dwell: 'R3 · Object dwell',
  rapid_gathering: 'Rapid gathering',
  abandoned_after_owner_left: 'Abandoned bag',
  bag_taken_by_other_person: 'Bag handoff',
  after_hours_presence: 'After-hours presence',
  vehicle_in_pedestrian_zone: 'Vehicle in pedestrian zone',
};

function formatRuleName(rule) {
  if (!rule) return 'Unknown rule';
  if (RULE_LABELS[rule]) return RULE_LABELS[rule];
  const readable = String(rule).replace(/_/g, ' ');
  return readable.charAt(0).toUpperCase() + readable.slice(1);
}

function summarizeAnomalyDetail(detail) {
  if (!detail) return '-';
  return String(detail).replace(/\s*\[agent:[\s\S]*\]$/i, '').trim() || String(detail);
}

/**
 * Clean line chart of recent per-frame person detections against the R1 threshold.
 */
function OccupancyChart({ samples }) {
  const width = 460;
  const height = 148;
  const pad = { top: 12, right: 64, bottom: 24, left: 28 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxCount = Math.max(
    4,
    ...samples.map((item) => Number(item.count) || 0)
  );
  // Keep even scale ticks (0, 2, 4, 6...) so neutral gridlines never collide with Limit (> 3).
  const yMax = Math.ceil(maxCount / 2) * 2;

  const yPos = (val) => pad.top + plotH - (val / yMax) * plotH;
  const xPos = (idx, total) => {
    if (total <= 1) return pad.left + plotW / 2;
    return pad.left + (idx / (total - 1)) * plotW;
  };

  const yTicks =
    yMax === 4
      ? [0, 2, 4]
      : yMax === 6
        ? [0, 2, 4, 6]
        : [0, Math.round(yMax / 2), yMax];
  const thresholdY = yPos(R1_PERSON_THRESHOLD);

  const points = samples
    .map((item, idx) => `${xPos(idx, samples.length).toFixed(1)},${yPos(Number(item.count) || 0).toFixed(1)}`)
    .join(' ');

  const firstTs = samples.length ? formatClock(samples[0].ts) : '-';
  const lastTs = samples.length ? formatClock(samples[samples.length - 1].ts) : '-';

  return (
    <div className="chart-wrap">
      <svg
        className="chart-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Person count over recent frames compared to threshold of 3"
      >
        {yTicks.map((tick) => {
          const y = yPos(tick);
          return (
            <g key={tick}>
              <line
                x1={pad.left}
                y1={y}
                x2={width - pad.right}
                y2={y}
                stroke={tick === 0 ? 'var(--border)' : 'var(--rule)'}
                strokeWidth="1"
              />
              <text
                x={pad.left - 6}
                y={y + 3.5}
                textAnchor="end"
                className="mono chart-axis-text"
              >
                {tick}
              </text>
            </g>
          );
        })}

        <line
          x1={pad.left}
          y1={thresholdY}
          x2={width - pad.right}
          y2={thresholdY}
          stroke="var(--crit-rule)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <text
          x={width - pad.right + 8}
          y={thresholdY + 3.5}
          textAnchor="start"
          className="chart-limit-text"
        >
          Limit (&gt; {R1_PERSON_THRESHOLD})
        </text>

        {samples.length === 1 && (
          <circle
            cx={xPos(0, 1)}
            cy={yPos(Number(samples[0].count) || 0)}
            r="3"
            fill="var(--accent)"
          />
        )}

        {samples.length > 1 && (
          <polyline
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={points}
          />
        )}

        <text x={pad.left} y={height - 6} textAnchor="start" className="mono chart-axis-text">
          {firstTs}
        </text>
        <text x={width - pad.right} y={height - 6} textAnchor="end" className="mono chart-axis-text">
          {lastTs}
        </text>
      </svg>
    </div>
  );
}

/**
 * Analytics Console (:5173): real-time YOLO26n stream, telemetry strip, anomalies, events, and nodes.
 */
export default function AnalyticsApp() {
  const [activeTab, setActiveTab] = useState('live');
  const [stats, setStats] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [events, setEvents] = useState([]);
  const [devices, setDevices] = useState([]);
  const [health, setHealth] = useState(null);
  const [frameUrl, setFrameUrl] = useState('');
  const [lastSyncTs, setLastSyncTs] = useState(null);
  const [fetchError, setFetchError] = useState('');

  const peerUrl = useMemo(() => {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:5174`;
  }, []);

  useEffect(() => {
    let alive = true;
    let inFlight = false;

    async function pollTelemetry() {
      if (inFlight) return;
      inFlight = true;
      try {
        const headers = buildHeaders();
        const [statsRes, anomRes, evtRes, devRes, healthRes] = await Promise.all([
          fetch(`${API_BASE}/stats`, { headers }),
          fetch(`${API_BASE}/anomalies?limit=60`, { headers }),
          fetch(`${API_BASE}/events?limit=120`, { headers }),
          fetch(`${API_BASE}/devices`, { headers }),
          fetch(`${API_BASE}/health`, { headers }),
        ]);

        if (!statsRes.ok) {
          throw new Error(`HTTP ${statsRes.status}`);
        }

        const [nextStats, nextAnom, nextEvt, nextDev, nextHealth] = await Promise.all([
          statsRes.json(),
          anomRes.ok ? anomRes.json() : [],
          evtRes.ok ? evtRes.json() : [],
          devRes.ok ? devRes.json() : [],
          healthRes.ok ? healthRes.json() : null,
        ]);

        if (!alive) return;
        setStats(nextStats);
        setAnomalies(Array.isArray(nextAnom) ? nextAnom : []);
        setEvents(Array.isArray(nextEvt) ? nextEvt : []);
        setDevices(Array.isArray(nextDev) ? nextDev : []);
        setHealth(nextHealth);
        setLastSyncTs(Date.now() / 1000);
        setFetchError('');
      } catch (err) {
        if (!alive) return;
        setFetchError(err instanceof Error ? err.message : 'Backend unavailable');
      } finally {
        inFlight = false;
      }
    }

    pollTelemetry();
    const timer = window.setInterval(pollTelemetry, POLL_TELEMETRY_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    let inFlight = false;
    let currentObjectUrl = '';

    async function pollFrame() {
      if (inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`${API_BASE}/frames/latest?t=${Date.now()}`, {
          headers: buildHeaders(),
        });
        if (!res.ok || res.status === 204) return;
        const blob = await res.blob();
        if (!alive || blob.size === 0) return;

        const nextUrl = URL.createObjectURL(blob);
        if (currentObjectUrl) {
          URL.revokeObjectURL(currentObjectUrl);
        }
        currentObjectUrl = nextUrl;
        setFrameUrl(nextUrl);
      } catch {
        // Keep last valid frame visible during transient stalls.
      } finally {
        inFlight = false;
      }
    }

    pollFrame();
    const timer = window.setInterval(pollFrame, POLL_FRAME_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
      if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
      }
    };
  }, []);

  const latestAnomaly = anomalies[0] || null;
  const nowSec = Date.now() / 1000;
  const hasActiveAlert = Boolean(
    latestAnomaly && nowSec - Number(latestAnomaly.ts || 0) <= ACTIVE_ALERT_WINDOW_S
  );

  const personSamples = useMemo(() => {
    const filtered = events
      .filter((evt) => evt.object_class === 'person')
      .slice(0, 30)
      .reverse();
    return filtered;
  }, [events]);

  const byRule = stats?.anomalies_by_rule || {};
  const primaryDevice = devices[0]?.device_id || null;
  const statusTone = fetchError ? 'warn' : hasActiveAlert ? 'crit' : 'live';
  const topMeta = fetchError
    ? 'Backend offline'
    : primaryDevice
      ? `${primaryDevice} · ${(stats?.fps ?? 0).toFixed(1)} FPS`
      : `0 nodes · ${(stats?.fps ?? 0).toFixed(1)} FPS`;

  const metrics = [
    {
      label: 'Total events',
      value: stats?.total_events ?? 0,
    },
    {
      label: 'Occupancy spikes',
      value: byRule.occupancy_spike ?? 0,
    },
    {
      label: 'Unexpected objects',
      value: byRule.unexpected_object ?? 0,
    },
    {
      label: 'Object dwell',
      value: byRule.object_dwell ?? 0,
    },
    {
      label: 'Pipeline FPS',
      value: (stats?.fps ?? 0).toFixed(1),
      unit: 'fps',
    },
    {
      label: 'Inf / E2E latency',
      value: (stats?.avg_inference_ms ?? 0).toFixed(1),
      unit: `/ ${Math.round(stats?.avg_e2e_ms ?? 0)}ms`,
    },
  ];

  const tabs = [
    { id: 'live', label: 'Live Monitor' },
    {
      id: 'anomalies',
      label: 'Anomalies',
      badge: anomalies.length > 0 ? anomalies.length : '',
      badgeAlert: hasActiveAlert,
    },
    {
      id: 'detections',
      label: 'Detections',
      badge: events.length > 0 ? events.length : '',
    },
    {
      id: 'nodes',
      label: 'Nodes & Rules',
      badge: devices.length > 0 ? devices.length : '',
    },
  ];

  const subtitleText = health?.model
    ? `${health.model} ONNX worker · SQLite WAL stream · ${devices.length} connected node${devices.length === 1 ? '' : 's'}`
    : 'Real-time YOLO26n ONNX anomaly detection and telemetry console';

  const headerStamp = fetchError
    ? `Disconnected (${fetchError})`
    : lastSyncTs
      ? `Updated ${formatClock(lastSyncTs)}`
      : 'Connecting…';

  return (
    <div className="console-shell">
      <ConsoleTopBar
        title="Analytics Console"
        port="5173"
        statusTone={statusTone}
        metaText={topMeta}
        peerLabel="Edge Control Deck (:5174)"
        peerHref={peerUrl}
      />

      <ConsolePageHeader
        title="Live Pipeline Monitor"
        subtitle={subtitleText}
        stamp={headerStamp}
      />

      {fetchError && (
        <div className="notice-bar notice-bar--warn" role="status">
          <div className="notice-main">
            <span className="notice-title">Backend connection stalled</span>
            <span>
              Unable to reach {API_BASE}/stats ({fetchError}). Retrying automatically.
            </span>
          </div>
        </div>
      )}

      {!fetchError && hasActiveAlert && latestAnomaly && (
        <div className="notice-bar notice-bar--crit" role="alert">
          <div className="notice-main">
            <span className="notice-title">
              Active alert · {formatRuleName(latestAnomaly.rule)}
            </span>
            <span>
              {summarizeAnomalyDetail(latestAnomaly.detail)} ({latestAnomaly.device_id} at{' '}
              {formatClock(latestAnomaly.ts)})
            </span>
          </div>
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => setActiveTab('anomalies')}
          >
            Open Anomalies
          </button>
        </div>
      )}

      <MetricStrip metrics={metrics} />

      <TabBar
        tabs={tabs}
        activeTab={activeTab}
        onChange={setActiveTab}
        ariaLabel="Analytics Console sections"
      />

      {activeTab === 'live' && (
        <section className="split-grid" aria-labelledby="tab-live">
          <article className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Annotated YOLO26n Feed</h2>
              <span className="panel-meta">
                Queue {stats?.queue_depth ?? 0} · {(stats?.avg_frame_kb ?? 0).toFixed(1)} KB avg
              </span>
            </div>

            <div className="video-stage">
              {frameUrl ? (
                <img
                  className="video-frame"
                  src={frameUrl}
                  alt="Live annotated server video stream"
                />
              ) : (
                <div className="video-empty">
                  <div>Waiting for annotated video frames</div>
                  <div className="video-empty-sub">
                    Start streaming from Edge Control Deck (:5174) or POST /frames
                  </div>
                </div>
              )}
            </div>

            <div className="video-caption">
              <span>
                {frameUrl
                  ? 'Rendering bounding-box JPEG frames from backend pipeline'
                  : 'No processed frame cached yet'}
              </span>
              <span className="mono">
                Rx {stats?.frames_received ?? 0} · Drop {stats?.frames_dropped ?? 0} · Uptime{' '}
                {formatDuration(stats?.uptime_s)}
              </span>
            </div>
          </article>

          <div className="stack-col">
            <article className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Person Count Timeline</h2>
                <span className="panel-meta">
                  {personSamples.length
                    ? `Latest ${personSamples.length} samples`
                    : 'No samples yet'}
                </span>
              </div>
              <OccupancyChart samples={personSamples} />
            </article>

            <article className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Recent Anomaly Triggers</h2>
                <button
                  type="button"
                  className="btn btn--sm"
                  onClick={() => setActiveTab('anomalies')}
                >
                  View all
                </button>
              </div>

              {anomalies.length === 0 ? (
                <div className="empty-state">No anomaly triggers logged yet.</div>
              ) : (
                <div className="compact-list">
                  {anomalies.slice(0, 3).map((item, idx) => (
                    <div className="compact-row" key={`${item.ts}-${item.device_id}-${idx}`}>
                      <div className="compact-row-main">
                        <div className="compact-row-top">
                          <span className={`pill pill--${item.severity || 'info'}`}>
                            {item.severity || 'info'}
                          </span>
                          <span>{formatRuleName(item.rule)}</span>
                          <span className="mono muted">{item.device_id}</span>
                        </div>
                        <div className="compact-row-detail">
                          {summarizeAnomalyDetail(item.detail)}
                        </div>
                      </div>
                      <span className="mono compact-row-time">{formatClock(item.ts)}</span>
                    </div>
                  ))}
                </div>
              )}
            </article>
          </div>
        </section>
      )}

      {activeTab === 'anomalies' && (
        <section className="panel panel--flush" aria-labelledby="tab-anomalies">
          <div className="panel-head">
            <h2 className="panel-title">Anomaly Log</h2>
            <span className="panel-meta">{anomalies.length} recent records</span>
          </div>

          {anomalies.length === 0 ? (
            <div className="empty-state">No anomalies recorded in this session.</div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Device</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((item, idx) => (
                    <tr key={`${item.ts}-${item.device_id}-${idx}`}>
                      <td className="mono col-nowrap">{formatClock(item.ts)}</td>
                      <td className="mono col-nowrap">{item.device_id}</td>
                      <td className="mono col-nowrap">{item.rule}</td>
                      <td className="col-nowrap">
                        <span className={`pill pill--${item.severity || 'info'}`}>
                          {item.severity || 'info'}
                        </span>
                      </td>
                      <td>{item.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === 'detections' && (
        <section className="panel panel--flush" aria-labelledby="tab-detections">
          <div className="panel-head">
            <h2 className="panel-title">Detection Events</h2>
            <span className="panel-meta">{events.length} recent records</span>
          </div>

          {events.length === 0 ? (
            <div className="empty-state">Waiting for object detection events from worker.</div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Device</th>
                    <th>Source</th>
                    <th>Class</th>
                    <th className="num">Count</th>
                    <th className="num">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((evt, idx) => (
                    <tr key={`${evt.ts}-${evt.device_id}-${evt.object_class}-${idx}`}>
                      <td className="mono col-nowrap">{formatClock(evt.ts)}</td>
                      <td className="mono col-nowrap">{evt.device_id}</td>
                      <td className="mono muted col-nowrap">{evt.source}</td>
                      <td className="col-nowrap">{evt.object_class}</td>
                      <td className="num mono">{evt.count}</td>
                      <td className="num mono">
                        {evt.avg_conf !== undefined && evt.avg_conf !== null
                          ? `${Math.round(Number(evt.avg_conf) * 100)}%`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === 'nodes' && (
        <section className="split-grid split-grid--equal" aria-labelledby="tab-nodes">
          <article className="panel panel--flush">
            <div className="panel-head">
              <h2 className="panel-title">Connected Edge Nodes</h2>
              <span className="panel-meta">{devices.length} active</span>
            </div>

            {devices.length === 0 ? (
              <div className="empty-state">No edge devices have reported frames yet.</div>
            ) : (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Device ID</th>
                      <th>Source Kind</th>
                      <th className="num">Frames Received</th>
                      <th className="num">Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {devices.map((dev) => (
                      <tr key={dev.device_id}>
                        <td className="mono">{dev.device_id}</td>
                        <td className="mono muted">{dev.source_kind || '-'}</td>
                        <td className="num mono">{dev.frames_received ?? 0}</td>
                        <td className="num mono">{formatClock(dev.last_seen_ts)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>

          <article className="panel panel--flush">
            <div className="panel-head">
              <h2 className="panel-title">System Health &amp; Anomaly Rules</h2>
              <span className="pill pill--ok">{health?.status || 'unknown'}</span>
            </div>

            <div className="panel-body">
              <div className="kv-list">
                <div className="kv-row">
                  <span className="kv-key">Inference model</span>
                  <span className="kv-val">{health?.model || '-'}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">SQLite store</span>
                  <span className="kv-val">{health?.db || '-'}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Worker status</span>
                  <span className="kv-val">{health?.worker || '-'}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">R1 · occupancy_spike</span>
                  <span className="kv-val">person count &gt; 3 per frame</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">R2 · unexpected_object</span>
                  <span className="kv-val">non-desk object persists &gt; 5s</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">R3 · object_dwell</span>
                  <span className="kv-val">unattended item stationary &ge; 30s</span>
                </div>
              </div>
            </div>
          </article>
        </section>
      )}
    </div>
  );
}
