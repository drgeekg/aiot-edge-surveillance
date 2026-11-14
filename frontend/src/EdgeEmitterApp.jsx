import React, { useEffect, useState } from 'react';
import { AnimatedTabBar, CustomCursor, HeroHeader } from './components/GlassShell';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ANALYTICS_FRONTEND_URL = import.meta.env.VITE_ANALYTICS_UI_URL || 'http://localhost:5173';
const API_KEY = import.meta.env.VITE_API_KEY || '';
/** Build fetch headers and attach X-API-Key when configured via VITE_API_KEY. */
const apiHeaders = (extra = {}) => (API_KEY ? { 'X-API-Key': API_KEY, ...extra } : { ...extra });

const TABS = [
  { id: 'source', icon: '🎬', label: 'Video Source Switcher' },
  { id: 'encoder', icon: '🎛️', label: 'Encoder & Bandwidth' },
  { id: 'inject', icon: '🧪', label: 'Synthetic Anomaly Injector' },
];

/**
 * Edge Emitter Control Deck (:5174): hot-swaps edge video sources, tunes JPEG/FPS settings, and injects synthetic events.
 */
export default function EdgeEmitterApp() {
  const [activeTab, setActiveTab] = useState('source');
  const [edge, setEdge] = useState({
    source: 'data/demo.mp4',
    device_id: 'edge-01',
    fps: 5,
    width: 640,
    quality: 70,
    streaming: true,
    frames_sent: 0,
    window_fps: 0,
    window_kbps: 0,
    last_frame_kb: 0,
    server_queue_depth: 0,
    status_msg: 'Connecting...',
    available_sources: [],
  });
  const [customSrc, setCustomSrc] = useState('http://192.168.1.10:8080/video');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [frameUrl, setFrameUrl] = useState(null);
  const [toastMsg, setToastMsg] = useState('');

  /** Display a temporary confirmation banner for 3.2 seconds after control actions. */
  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3200);
  };

  /** Push a partial edge configuration update to POST /edge/config and refresh status state. */
  const updateEdgeConfig = async (patch, label) => {
    try {
      const res = await fetch(`${API_BASE}/edge/config`, {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(patch),
      });
      if (res.ok) {
        const data = await res.json();
        setEdge(data);
        if (label) showToast(label);
      }
    } catch {
      showToast('Failed to reach Edge API');
    }
  };

  useEffect(() => {
    let mounted = true;
    /** Poll GET /edge/status for live capture config, uplink throughput, and available sources. */
    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/edge/status`, { headers: apiHeaders() });
        if (res.ok && mounted) {
          setEdge(await res.json());
        }
      } catch {
        // Ignore transient error
      }
    };
    pollStatus();
    const id = setInterval(pollStatus, 500);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    let prevUrl = null;
    /** Poll GET /edge/frame for raw pre-inference JPEG previews using Blob URL swapping. */
    const pollEdgeFrame = async () => {
      try {
        const res = await fetch(`${API_BASE}/edge/frame?t=${Date.now()}`, { headers: apiHeaders() });
        if (!res.ok) return;
        const blob = await res.blob();
        if (!mounted || blob.size === 0) return;
        const nextUrl = URL.createObjectURL(blob);
        setFrameUrl(nextUrl);
        if (prevUrl) URL.revokeObjectURL(prevUrl);
        prevUrl = nextUrl;
      } catch {
        // Ignore when warming up
      }
    };
    pollEdgeFrame();
    const id = setInterval(pollEdgeFrame, 260);
    return () => {
      mounted = false;
      clearInterval(id);
      if (prevUrl) URL.revokeObjectURL(prevUrl);
    };
  }, []);

  /** Fire synthetic R1/R2/R3 detection payloads into POST /events to test rule engine alerts. */
  const injectEvent = async (type) => {
    const now = Date.now() / 1000;
    try {
      if (type === 'r1') {
        const res = await fetch(`${API_BASE}/events`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            ts: now,
            source: 'edge-deck',
            device_id: edge.device_id,
            object_class: 'person',
            count: 5,
            avg_conf: 0.93,
          }),
        });
        const out = await res.json();
        showToast(`Fired R1 Occupancy Spike (${out.anomalies?.length || 0} alert)`);
      } else if (type === 'r2') {
        const box = [0.24, 0.24, 0.44, 0.44];
        await fetch(`${API_BASE}/events`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            ts: now - 6.0,
            source: 'edge-deck',
            device_id: `${edge.device_id}-r2`,
            object_class: 'backpack',
            count: 1,
            avg_conf: 0.89,
            box,
          }),
        });
        const res = await fetch(`${API_BASE}/events`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            ts: now,
            source: 'edge-deck',
            device_id: `${edge.device_id}-r2`,
            object_class: 'backpack',
            count: 1,
            avg_conf: 0.89,
            box,
          }),
        });
        const out = await res.json();
        showToast(`Fired R2 Unexpected Backpack (${out.anomalies?.length || 0} alert)`);
      } else if (type === 'r3') {
        const box = [0.4, 0.55, 0.55, 0.85];
        await fetch(`${API_BASE}/events`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            ts: now - 31.0,
            source: 'edge-deck',
            device_id: `${edge.device_id}-r3`,
            object_class: 'suitcase',
            count: 1,
            avg_conf: 0.95,
            box,
          }),
        });
        const res = await fetch(`${API_BASE}/events`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            ts: now,
            source: 'edge-deck',
            device_id: `${edge.device_id}-r3`,
            object_class: 'suitcase',
            count: 1,
            avg_conf: 0.95,
            box,
          }),
        });
        const out = await res.json();
        showToast(`Fired R3 Unattended Suitcase Dwell (${out.anomalies?.length || 0} alert)`);
      }
    } catch {
      showToast('Failed to inject synthetic event');
    }
  };

  const sources = edge.available_sources?.length
    ? edge.available_sources
    : [
        { id: 'data/demo.mp4', label: 'Unattended Bag Scenario (data/demo.mp4)', tag: 'Triggers R2 & R3' },
        { id: 'data/demo_attended.mp4', label: 'Attended Bag & Crowd Scenario (data/demo_attended.mp4)', tag: 'Triggers R1' },
        { id: '0', label: 'Integrated / USB Webcam (Index 0)', tag: 'Live Camera' },
      ];

  const knownIds = new Set(sources.map((s) => s.id));
  const isCustomActive = Boolean(edge.source) && !knownIds.has(edge.source);
  const dropdownValue = showCustomInput || isCustomActive ? '__other__' : edge.source;

  return (
    <div className="app-container">
      <CustomCursor />

      <HeroHeader
        badge="Edge Emitter Control Deck · Pipeline Producer"
        title="Edge Video Source & Uplink Deck"
        subtitle="Hot-swap video streams, tune JPEG compression & emit data onto the analysis pipeline"
        peerUrl={ANALYTICS_FRONTEND_URL}
        peerLabel="Open Server Analytics (:5173)"
      />

      {toastMsg && (
        <div
          className="glass-card"
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1.15rem',
            borderColor: 'rgba(107, 194, 148, 0.55)',
            background: 'rgba(28, 52, 38, 0.65)',
            fontSize: '0.85rem',
            fontWeight: 600,
          }}
        >
          ✓ {toastMsg}
        </div>
      )}

      <section className="kpi-grid">
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Active Source</div>
          <div className="kpi-value" style={{ fontSize: '1.05rem', wordBreak: 'break-all' }}>
            {edge.source}
          </div>
          <div className="kpi-sub">{edge.status_msg}</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Outbound FPS</div>
          <div className="kpi-value">{edge.window_fps}</div>
          <div className="kpi-sub">Target: {edge.fps} FPS</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Uplink Bandwidth</div>
          <div className="kpi-value">{edge.window_kbps} <span style={{ fontSize: '0.9rem' }}>KB/s</span></div>
          <div className="kpi-sub">HTTP POST /frames</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Frame Payload</div>
          <div className="kpi-value">{edge.last_frame_kb} <span style={{ fontSize: '0.9rem' }}>KB</span></div>
          <div className="kpi-sub">{edge.width}px · q={edge.quality}</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Frames Emitted</div>
          <div className="kpi-value">{edge.frames_sent}</div>
          <div className="kpi-sub">Node: {edge.device_id}</div>
        </div>
        <div className="glass-card kpi-tile">
          <div className="kpi-label">Server Queue</div>
          <div className="kpi-value">{edge.server_queue_depth}/8</div>
          <div className="kpi-sub">Ingest backpressure</div>
        </div>
      </section>

      <AnimatedTabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'source' && (
        <div className="split-grid">
          <div className="glass-card">
            <div className="section-kicker">Hot-Swap Input Feed</div>
            <h2 className="section-heading">Select Active Video Source</h2>
            <p style={{ fontSize: '0.83rem', color: 'var(--latte)', marginBottom: '0.95rem' }}>
              Switching source here immediately swaps the live video stream emitted to the Server Analytics pipeline (:5173).
            </p>

            <div style={{ display: 'grid', gap: '0.75rem' }}>
              <select
                className="glass-input"
                aria-label="Select video source"
                value={dropdownValue}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '__other__') {
                    setShowCustomInput(true);
                  } else {
                    setShowCustomInput(false);
                    updateEdgeConfig({ source: val, streaming: true }, `Switched stream to ${val}`);
                  }
                }}
              >
                {sources.map((s) => (
                  <option key={s.id} value={s.id} style={{ background: '#1a120d', color: '#f6ede4' }}>
                    {s.label} — [{s.tag}]
                  </option>
                ))}
                <option value="__other__" style={{ background: '#1a120d', color: '#f6ede4' }}>
                  Other (Custom File / YouTube / RTSP URL)...
                </option>
              </select>

              <div className="mono" style={{ fontSize: '0.74rem', color: 'var(--mocha)' }}>
                active source: {edge.source}
              </div>
            </div>

            {(showCustomInput || isCustomActive) && (
              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(246, 237, 228, 0.1)' }}>
                <div className="kpi-label" style={{ marginBottom: '0.45rem' }}>
                  Custom File Path / YouTube URL / RTSP / IP Camera URL
                </div>
                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  <input
                    className="glass-input"
                    value={customSrc}
                    onChange={(e) => setCustomSrc(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=... or data/demo.mp4"
                  />
                  <button
                    className="glass-btn"
                    onClick={() => updateEdgeConfig({ source: customSrc.trim(), streaming: true }, `Switched to ${customSrc.trim()}`)}
                  >
                    Stream URL
                  </button>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.1rem' }}>
              <button
                className="glass-btn"
                style={{ width: '100%' }}
                onClick={() =>
                  updateEdgeConfig(
                    { streaming: !edge.streaming },
                    edge.streaming ? 'Paused uplink stream' : 'Resumed uplink stream'
                  )
                }
              >
                {edge.streaming ? '⏸ Pause Outbound Stream' : '▶ Resume Outbound Stream'}
              </button>
            </div>
          </div>

          <div className="glass-card">
            <div className="section-kicker">Raw Edge Capture (Pre-Inference)</div>
            <h2 className="section-heading">Outbound Frame Monitor</h2>
            <div className="video-stage">
              {frameUrl ? (
                <img src={frameUrl} alt="Raw edge outbound frame" />
              ) : (
                <div style={{ color: 'var(--mocha)', fontSize: '0.86rem' }}>
                  Capturing first frame from {edge.source}...
                </div>
              )}
              <div className="video-hud-pill">
                <span>Node: {edge.device_id}</span>
                <span>{edge.last_frame_kb} KB JPEG</span>
                <span>{edge.window_kbps} KB/s → :8000/frames</span>
              </div>
            </div>
            {edge.error_msg && (
              <div style={{ marginTop: '0.75rem', color: '#ff9485', fontSize: '0.8rem' }}>
                ⚠ {edge.error_msg}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'encoder' && (
        <div className="glass-card" style={{ maxWidth: '820px', margin: '0 auto' }}>
          <div className="section-kicker">Edge Compression & Throttling</div>
          <h2 className="section-heading">Live Uplink Encoder Controls</h2>

          <div style={{ display: 'grid', gap: '1.25rem', marginTop: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="kpi-label">Target Frame Rate (FPS)</span>
                <span className="mono">{edge.fps} FPS</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={edge.fps}
                style={{ width: '100%', accentColor: '#d88f56' }}
                onChange={(e) => updateEdgeConfig({ fps: Number(e.target.value) })}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="kpi-label">Resize Frame Width (px)</span>
                <span className="mono">{edge.width} px</span>
              </div>
              <input
                type="range"
                min="320"
                max="1280"
                step="160"
                value={edge.width}
                style={{ width: '100%', accentColor: '#d88f56' }}
                onChange={(e) => updateEdgeConfig({ width: Number(e.target.value) })}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span className="kpi-label">JPEG Compression Quality</span>
                <span className="mono">{edge.quality}%</span>
              </div>
              <input
                type="range"
                min="30"
                max="95"
                step="5"
                value={edge.quality}
                style={{ width: '100%', accentColor: '#d88f56' }}
                onChange={(e) => updateEdgeConfig({ quality: Number(e.target.value) })}
              />
            </div>

            <div>
              <div className="kpi-label" style={{ marginBottom: '0.4rem' }}>Edge Device Identifier</div>
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <input
                  className="glass-input"
                  defaultValue={edge.device_id}
                  onBlur={(e) => updateEdgeConfig({ device_id: e.target.value.trim() || 'edge-01' }, 'Updated device ID')}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'inject' && (
        <div className="glass-card" style={{ maxWidth: '920px', margin: '0 auto' }}>
          <div className="section-kicker">Edge-Inference JSON Seam (POST /events)</div>
          <h2 className="section-heading">Synthetic Anomaly Rule Triggers</h2>
          <p style={{ fontSize: '0.84rem', color: 'var(--latte)', marginBottom: '1.2rem' }}>
            Inject scripted detections directly into the server rule engine to verify R1, R2, and R3 alerts on the Analytics Console (:5173).
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.9rem' }}>
            <button className="glass-btn" onClick={() => injectEvent('r1')} style={{ padding: '1.15rem' }}>
              <div style={{ fontSize: '1.3rem', marginBottom: '0.35rem' }}>👥</div>
              <div>Trigger R1 · Occupancy Spike</div>
              <div className="kpi-sub" style={{ color: 'var(--latte)' }}>Injects 5 persons (&gt;3 threshold)</div>
            </button>

            <button className="glass-btn" onClick={() => injectEvent('r2')} style={{ padding: '1.15rem' }}>
              <div style={{ fontSize: '1.3rem', marginBottom: '0.35rem' }}>🎒</div>
              <div>Trigger R2 · Unexpected Object</div>
              <div className="kpi-sub" style={{ color: 'var(--latte)' }}>Injects backpack present &ge;6s</div>
            </button>

            <button className="glass-btn" onClick={() => injectEvent('r3')} style={{ padding: '1.15rem' }}>
              <div style={{ fontSize: '1.3rem', marginBottom: '0.35rem' }}>🧳</div>
              <div>Trigger R3 · Unattended Dwell</div>
              <div className="kpi-sub" style={{ color: 'var(--latte)' }}>Injects suitcase unattended &ge;31s</div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
