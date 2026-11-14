import React, { useEffect, useState } from 'react';
import { AnimatedTabBar, CustomCursor, HeroHeader } from './components/GlassShell';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const EDGE_FRONTEND_URL = import.meta.env.VITE_EDGE_UI_URL || 'http://localhost:5174';
const API_KEY = import.meta.env.VITE_API_KEY || '';
/** Build fetch headers and attach X-API-Key when configured via VITE_API_KEY. */
const apiHeaders = (extra = {}) => (API_KEY ? { 'X-API-Key': API_KEY, ...extra } : { ...extra });

const TABS = [
  { id: 'live', icon: '◉', label: 'Live Monitor' },
  { id: 'anomalies', icon: '⚡', label: 'Anomaly Vault' },
  { id: 'events', icon: '📦', label: 'Detection Ledger' },
  { id: 'nodes', icon: '🛰️', label: 'Nodes & Rules' },
];

/**
 * Render an inline SVG area/line timeline of recent person counts with a dashed R1 threshold line.
 */
function OccupancyChart({ events }) {
  const personRows = events
    .filter((e) => e.object_class === 'person')
    .slice(0, 32)
    .reverse();

  if (personRows.length < 2) {
    return (
      <div style={{ padding: '2.2rem 0', textAlign: 'center', color: 'var(--mocha)', fontSize: '0.84rem' }}>
        Waiting for person detections to plot timeline...
      </div>
    );
  }

  const maxCount = Math.max(4, ...personRows.map((r) => Number(r.count || 0)));
  const w = 520;
  const h = 155;
  const pad = 16;

  const pts = personRows.map((r, i) => {
    const x = pad + (i / (personRows.length - 1)) * (w - pad * 2);
    const y = h - pad - (Number(r.count || 0) / maxCount) * (h - pad * 2);
    return [x, y];
  });

  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L${pts[pts.length - 1][0].toFixed(1)},${h - pad} L${pts[0][0].toFixed(1)},${h - pad} Z`;

  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: '165px', overflow: 'visible' }}>
        <defs>
          <linearGradient id="coffeeArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d88f56" stopOpacity="0.52" />
            <stop offset="100%" stopColor="#d88f56" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <line
          x1={pad}
          y1={h - pad - (3 / maxCount) * (h - pad * 2)}
          x2={w - pad}
          y2={h - pad - (3 / maxCount) * (h - pad * 2)}
          stroke="rgba(229, 92, 73, 0.45)"
          strokeDasharray="4 4"
          strokeWidth="1"
        />
        <path d={areaPath} fill="url(#coffeeArea)" />
        <path d={linePath} fill="none" stroke="#eba872" strokeWidth="2.4" strokeLinecap="round" />
        {pts.map((p, idx) => (
          <circle key={idx} cx={p[0]} cy={p[1]} r="3" fill="#f6ede4" />
        ))}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.73rem', color: 'var(--mocha)' }}>
        <span className="mono">
          {new Date(personRows[0].ts * 1000).toLocaleTimeString()}
        </span>
        <span>Dashed red line: R1 threshold (&gt;3 persons)</span>
        <span className="mono">
          {new Date(personRows[personRows.length - 1].ts * 1000).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

/**
 * Server Analytics Console (:5173): polls backend telemetry, anomalies, events, health, and live frames.
 */
export default function AnalyticsApp() {
  const [activeTab, setActiveTab] = useState('live');
  const [stats, setStats] = useState({});
  const [anomalies, setAnomalies] = useState([]);
  const [events, setEvents] = useState([]);
  const [devices, setDevices] = useState([]);
  const [health, setHealth] = useState({});
  const [frameUrl, setFrameUrl] = useState(null);

  // Poll JSON telemetry every 650ms
  useEffect(() => {
    let mounted = true;
    /** Fetch all JSON telemetry endpoints in parallel and guard state updates against unmount. */
    const pollTelemetry = async () => {
      try {
        const hdrs = { headers: apiHeaders() };
        const [sRes, aRes, eRes, dRes, hRes] = await Promise.all([
          fetch(`${API_BASE}/stats`, hdrs),
          fetch(`${API_BASE}/anomalies?limit=60`, hdrs),
          fetch(`${API_BASE}/events?limit=120`, hdrs),
          fetch(`${API_BASE}/devices`, hdrs),
          fetch(`${API_BASE}/health`, hdrs),
        ]);
        if (!mounted) return;
        if (sRes.ok) setStats(await sRes.json());
        if (aRes.ok) setAnomalies(await aRes.json());
        if (eRes.ok) setEvents(await eRes.json());
        if (dRes.ok) setDevices(await dRes.json());
        if (hRes.ok) setHealth(await hRes.json());
      } catch {
        // Ignore transient network hiccups
      }
    };
    pollTelemetry();
    const id = setInterval(pollTelemetry, 650);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  // Poll annotated JPEG frame every 260ms with zero-flicker Blob swap
  useEffect(() => {
    let mounted = true;
    let currentObjUrl = null;

    /** Fetch the latest annotated JPEG as a Blob URL and revoke the prior URL after swapping. */
    const pollFrame = async () => {
      try {
        const res = await fetch(`${API_BASE}/frames/latest?t=${Date.now()}`, { headers: apiHeaders() });
        if (!res.ok) return;
        const blob = await res.blob();
        if (!mounted || blob.size === 0) return;
        const nextUrl = URL.createObjectURL(blob);
        setFrameUrl(nextUrl);
        if (currentObjUrl) URL.revokeObjectURL(currentObjUrl);
        currentObjUrl = nextUrl;
      } catch {
        // Ignore when no frame yet
      }
    };
    pollFrame();
    const id = setInterval(pollFrame, 260);
    return () => {
      mounted = false;
      clearInterval(id);
      if (currentObjUrl) URL.revokeObjectURL(currentObjUrl);
    };
  }, []);

  const nowSec = Date.now() / 1000;
  const recentAlert =
    anomalies.length > 0 && nowSec - Number(anomalies[0].ts || 0) <= 15
      ? anomalies[0]
      : null;

  const byRule = stats.anomalies_by_rule || {};

  return (
    <div className="app-container">
      <CustomCursor />

      <HeroHeader
        badge="Server Analytics Console · Pipeline Consumer"
        title="Edge-to-Server Anomaly Intelligence"
        subtitle="Real-time YOLO26n ONNX inference, centroid tracking & R1/R2/R3 rule evaluation"
        peerUrl={EDGE_FRONTEND_URL}
        peerLabel="Open Edge Emitter Deck (:5174)"
      />

      {recentAlert && (
        <div className="alert-banner">
          <div>
            🚨 <strong>ACTIVE {String(recentAlert.severity || 'WARNING').toUpperCase()} ALERT</strong> ·{' '}
            <span className="mono">{recentAlert.rule}</span> — {recentAlert.detail}
          </div>
          <div className="mono" style={{ fontSize: '0.8rem', opacity: 0.9 }}>
            node: {recentAlert.device_id} · {Math.max(0, nowSec - recentAlert.ts).toFixed(1)}s ago
          </div>
        </div>
      )}

      <section className="kpi-grid">
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Total Events</div>
          <div className="kpi-value">{stats.total_events ?? 0}</div>
          <div className="kpi-sub">SQLite logged</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">R1 Occupancy Spike</div>
          <div className="kpi-value">{byRule.occupancy_spike ?? 0}</div>
          <div className="kpi-sub">&gt;3 persons in frame</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">R2 Unexpected Obj</div>
          <div className="kpi-value">{byRule.unexpected_object ?? 0}</div>
          <div className="kpi-sub">&ge;5s bag presence</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">R3 Object Dwell</div>
          <div className="kpi-value">{byRule.object_dwell ?? 0}</div>
          <div className="kpi-sub">&ge;30s unattended</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Pipeline FPS</div>
          <div className="kpi-value">{stats.fps ?? 'idle'}</div>
          <div className="kpi-sub">10s rolling window</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Inf / E2E Latency</div>
          <div className="kpi-value">
            {stats.avg_inference_ms ?? '-'} <span style={{ fontSize: '0.95rem', color: 'var(--latte)' }}>/ {stats.avg_e2e_ms ?? '-'}ms</span>
          </div>
          <div className="kpi-sub">ONNX CPU runtime</div>
        </div>
      </section>

      <AnimatedTabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'live' && (
        <div className="split-grid">
          <div className="glass-card">
            <div className="section-kicker">Computer Vision Output</div>
            <h2 className="section-heading">Annotated YOLO26n Stream</h2>
            <div className="video-stage">
              {frameUrl ? (
                <img src={frameUrl} alt="Live annotated stream" />
              ) : (
                <div style={{ color: 'var(--mocha)', fontSize: '0.88rem', padding: '1rem', textAlign: 'center' }}>
                  Waiting for annotated frame on <code>GET /frames/latest</code>...
                </div>
              )}
              <div className="video-hud-pill">
                <span>Payload: {stats.avg_frame_kb ?? '-'} KB avg</span>
                <span>Queue: {stats.queue_depth ?? 0}/8</span>
                <span>Dropped: {stats.frames_dropped ?? 0}</span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
            <div className="glass-card">
              <div className="section-kicker">Occupancy Telemetry</div>
              <h2 className="section-heading">Person Count Timeline</h2>
              <OccupancyChart events={events} />
            </div>

            <div className="glass-card">
              <div className="section-kicker">Rule Engine Pulse</div>
              <h2 className="section-heading">Recent Anomaly Triggers</h2>
              {anomalies.length === 0 ? (
                <p style={{ color: 'var(--mocha)', fontSize: '0.85rem' }}>
                  No anomaly triggers recorded yet. Switch video feed or inject events from the Edge Deck (:5174).
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {anomalies.slice(0, 5).map((a, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.6rem 0.85rem',
                        borderRadius: '13px',
                        background: 'rgba(18, 12, 9, 0.55)',
                        borderLeft: `3px solid ${a.severity === 'critical' ? 'var(--crimson)' : 'var(--amber)'}`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.82rem',
                      }}
                    >
                      <div>
                        <span className={`badge-sev ${a.severity === 'critical' ? 'badge-critical' : 'badge-warning'}`}>
                          {a.rule}
                        </span>{' '}
                        <span style={{ marginLeft: '0.4rem' }}>{a.detail}</span>
                      </div>
                      <span className="mono" style={{ color: 'var(--mocha)', fontSize: '0.75rem' }}>
                        {a.device_id} · {new Date(a.ts * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'anomalies' && (
        <div className="glass-card">
          <div className="section-kicker">Audit Log</div>
          <h2 className="section-heading">Triggered Anomalies (R1 · R2 · R3)</h2>
          <div className="glass-table-wrap">
            <table className="glass-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Rule</th>
                  <th>Edge Node</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <tr key={i}>
                    <td className="mono">{new Date(a.ts * 1000).toLocaleTimeString()}</td>
                    <td>
                      <span className={`badge-sev ${a.severity === 'critical' ? 'badge-critical' : 'badge-warning'}`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="mono">{a.rule}</td>
                    <td className="mono">{a.device_id}</td>
                    <td>{a.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'events' && (
        <div className="glass-card">
          <div className="section-kicker">SQLite Ingest Stream</div>
          <h2 className="section-heading">Recent Object Detections</h2>
          <div className="glass-table-wrap">
            <table className="glass-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Node</th>
                  <th>Source</th>
                  <th>Class</th>
                  <th>Count</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {events.slice(0, 60).map((e, i) => (
                  <tr key={i}>
                    <td className="mono">{new Date(e.ts * 1000).toLocaleTimeString()}</td>
                    <td className="mono">{e.device_id}</td>
                    <td className="mono">{e.source}</td>
                    <td style={{ fontWeight: 600, color: 'var(--caramel-glow)' }}>{e.object_class}</td>
                    <td className="mono">{e.count}</td>
                    <td className="mono">{(Number(e.avg_conf || 0) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'nodes' && (
        <div className="split-grid">
          <div className="glass-card">
            <div className="section-kicker">Telemetry Producers</div>
            <h2 className="section-heading">Connected Edge Nodes</h2>
            <div className="glass-table-wrap">
              <table className="glass-table">
                <thead>
                  <tr>
                    <th>Device ID</th>
                    <th>Kind</th>
                    <th>Frames Sent</th>
                    <th>Last Heartbeat</th>
                  </tr>
                </thead>
                <tbody>
                  {devices.map((d, i) => (
                    <tr key={i}>
                      <td className="mono" style={{ color: 'var(--caramel-glow)' }}>{d.device_id}</td>
                      <td className="mono">{d.source_kind}</td>
                      <td className="mono">{d.frames_received}</td>
                      <td className="mono">{Math.max(0, nowSec - d.last_seen_ts).toFixed(1)}s ago</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="glass-card">
            <div className="section-kicker">Engine Health & Config</div>
            <h2 className="section-heading">Active Rule Thresholds</h2>
            <pre
              className="mono"
              style={{
                background: 'rgba(14, 9, 6, 0.65)',
                padding: '1rem',
                borderRadius: '14px',
                border: '1px solid rgba(246, 237, 228, 0.1)',
                fontSize: '0.8rem',
                color: 'var(--crema)',
                overflowX: 'auto',
              }}
            >
              {JSON.stringify(
                {
                  status: health.status || 'online',
                  worker: health.worker || 'running',
                  model: health.model || 'yolo26n.onnx',
                  frames_received: stats.frames_received ?? 0,
                  frames_dropped: stats.frames_dropped ?? 0,
                  rules: health.rules || {},
                },
                null,
                2
              )}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
