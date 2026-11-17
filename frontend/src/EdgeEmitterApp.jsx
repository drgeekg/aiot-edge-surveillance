import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  API_BASE,
  ConsolePageHeader,
  ConsoleTopBar,
  MetricStrip,
  TabBar,
  buildHeaders,
  formatClock,
} from './components/ConsoleShell';

const POLL_STATUS_MS = 500;
const POLL_FRAME_MS = 260;
const EDGE_API_BASE = import.meta.env.VITE_EDGE_API_URL || 'http://localhost:8001';

const CLIP_RULE_HINTS = {
  'data/sec_cam_1.mp4': { mode: 'home', rules: ['H1 person_in_zone', 'H2 night_person', 'H11 vehicle_in_driveway', 'H3 loitering'] },
  'data/sec_cam_2.mp4': { mode: 'home', rules: ['H1 person_in_zone', 'H3 loitering', 'H9 person_down', 'H10 prolonged_inactivity'] },
  'data/sec_cam_3.mp4': { mode: 'home', rules: ['H11 vehicle_in_driveway', 'H12 vehicle_lingering', 'P13 vehicle_in_pedestrian_zone'] },
  'data/sec_cam_4.mp4': { mode: 'home', rules: ['H1 person_in_zone', 'H2 night_person', 'P5 restricted_area_intrusion'] },
  'data/demo.mp4': { mode: 'public', rules: ['R2 unexpected_object', 'R3 object_dwell'] },
  'data/demo_attended.mp4': { mode: 'public', rules: ['R1 occupancy_spike', 'R3 reset by owner'] },
  'data/people-detection.mp4': { mode: 'public', rules: ['P1 occupancy_spike', 'P8 rapid_gathering', 'P10 loitering'] },
  'data/person-bicycle-car.mp4': { mode: 'public', rules: ['P13 vehicle_in_pedestrian_zone', 'P15 no_wheels', 'H11 vehicle_in_driveway'] },
  'data/worker-zone.mp4': { mode: 'public', rules: ['P5 restricted_area_intrusion', 'P7 zone_crowd_density'] },
  'data/store-aisle.mp4': { mode: 'public', rules: ['P10 loitering', 'P18 queue_overflow'] },
  'data/car-detection.mp4': { mode: 'home', rules: ['H11 vehicle_in_driveway', 'H12 vehicle_lingering', 'P14 illegal_parking'] },
};

const SYNTHETIC_TRIGGERS = [
  {
    key: 'r1',
    mode: 'public',
    title: 'R1 · Occupancy Spike',
    sev: 'warning',
    desc: 'Posts 5 persons in frame (> 3 threshold).',
    meta: 'object_class: "person" · count: 5',
    btn: 'Trigger R1 · Occupancy Spike',
    events: (now) => [{ tsOffset: 0, object_class: 'person', count: 5, avg_conf: 0.93 }],
  },
  {
    key: 'r2',
    mode: 'public',
    title: 'R2 · Unexpected Object',
    sev: 'warning',
    desc: 'Posts backpack events 6s apart (>= 5s).',
    meta: 'object_class: "backpack" · window: -6s, now',
    btn: 'Trigger R2 · Unexpected Object',
    events: () => [
      { tsOffset: -6, object_class: 'backpack', count: 1, avg_conf: 0.89, box: [0.24, 0.24, 0.44, 0.44] },
      { tsOffset: 0, object_class: 'backpack', count: 1, avg_conf: 0.89, box: [0.24, 0.24, 0.44, 0.44] },
    ],
  },
  {
    key: 'r3',
    mode: 'public',
    title: 'R3 · Unattended Dwell',
    sev: 'critical',
    desc: 'Posts stationary suitcase 31s apart (>= 30s).',
    meta: 'object_class: "suitcase" · window: -31s, now',
    btn: 'Trigger R3 · Unattended Dwell',
    events: () => [
      { tsOffset: -31, object_class: 'suitcase', count: 1, avg_conf: 0.95, box: [0.4, 0.55, 0.55, 0.85] },
      { tsOffset: 0, object_class: 'suitcase', count: 1, avg_conf: 0.95, box: [0.4, 0.55, 0.55, 0.85] },
    ],
  },
  {
    key: 'p5',
    mode: 'public',
    title: 'P5 · Restricted Zone',
    sev: 'critical',
    desc: 'Person inside restricted zone polygon (>= 2s).',
    meta: 'zone: restricted · box: [0.05, 0.05, 0.20, 0.30]',
    btn: 'Trigger P5 · Restricted Zone',
    events: () => [
      { tsOffset: -3, object_class: 'person', count: 1, avg_conf: 0.91, box: [0.05, 0.05, 0.20, 0.30] },
      { tsOffset: 0, object_class: 'person', count: 1, avg_conf: 0.91, box: [0.05, 0.05, 0.20, 0.30] },
    ],
  },
  {
    key: 'p13',
    mode: 'public',
    title: 'P13 · Vehicle in Pedestrian',
    sev: 'critical',
    desc: 'Car inside pedestrian zone polygon.',
    meta: 'zone: pedestrian · object_class: "car"',
    btn: 'Trigger P13 · Vehicle Alert',
    events: () => [{ tsOffset: 0, object_class: 'car', count: 1, avg_conf: 0.9, box: [0.30, 0.50, 0.50, 0.80] }],
  },
  {
    key: 'h1',
    mode: 'home',
    arming: 'armed_night',
    title: 'H1/H2 · Door Intrusion',
    sev: 'warning',
    desc: 'Person enters door zone in armed_night mode (>= 2s).',
    meta: 'zone: door · box: [0.25, 0.45, 0.40, 0.90]',
    btn: 'Trigger H1/H2 · Door Zone',
    events: () => [
      { tsOffset: -3, object_class: 'person', count: 1, avg_conf: 0.92, box: [0.25, 0.45, 0.40, 0.90] },
      { tsOffset: 0, object_class: 'person', count: 1, avg_conf: 0.92, box: [0.25, 0.45, 0.40, 0.90] },
    ],
  },
  {
    key: 'h6',
    mode: 'home',
    arming: 'armed_away',
    title: 'H6 · Package Left at Door',
    sev: 'info',
    desc: 'Suitcase/parcel stationary in door zone (>= 10s).',
    meta: 'zone: door · window: -11s, now',
    btn: 'Trigger H6 · Parcel at Door',
    events: () => [
      { tsOffset: -11, object_class: 'suitcase', count: 1, avg_conf: 0.88, box: [0.25, 0.60, 0.35, 0.80] },
      { tsOffset: 0, object_class: 'suitcase', count: 1, avg_conf: 0.88, box: [0.25, 0.60, 0.35, 0.80] },
    ],
  },
  {
    key: 'h9',
    mode: 'home',
    arming: 'armed_home',
    title: 'H9 · Person Down',
    sev: 'critical',
    desc: 'Horizontal person aspect ratio (w/h >= 1.2) for 11s.',
    meta: 'box: [0.20, 0.60, 0.70, 0.80] · w/h: 2.5',
    btn: 'Trigger H9 · Person Down',
    events: () => [
      { tsOffset: -11, object_class: 'person', count: 1, avg_conf: 0.9, box: [0.20, 0.60, 0.70, 0.80] },
      { tsOffset: 0, object_class: 'person', count: 1, avg_conf: 0.9, box: [0.20, 0.60, 0.70, 0.80] },
    ],
  },
  {
    key: 'h11',
    mode: 'home',
    arming: 'armed_night',
    title: 'H11 · Vehicle in Driveway',
    sev: 'warning',
    desc: 'Car detected inside driveway polygon (sec_cam_1/3).',
    meta: 'zone: driveway · object_class: "car"',
    btn: 'Trigger H11 · Driveway Car',
    events: () => [{ tsOffset: 0, object_class: 'car', count: 1, avg_conf: 0.91, box: [0.65, 0.50, 0.90, 0.85] }],
  },
];

/**
 * Edge Control Deck (:5174): video source switcher, encoder settings, and synthetic R1/R2/R3 injector.
 */
export default function EdgeEmitterApp() {
  const [activeTab, setActiveTab] = useState('sources');
  const [edge, setEdge] = useState(null);
  const [modeState, setModeState] = useState({ mode: 'public', arming: 'armed_night' });
  const [frameUrl, setFrameUrl] = useState('');
  const [customSource, setCustomSource] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [draft, setDraft] = useState({
    fps: 5,
    width: 640,
    quality: 80,
    device_id: 'edge-01',
  });
  const [busyKey, setBusyKey] = useState('');
  const [notice, setNotice] = useState(null);
  const [lastSyncTs, setLastSyncTs] = useState(null);
  const [fetchError, setFetchError] = useState('');

  const editingUntilRef = useRef(0);
  const debounceTimerRef = useRef(null);

  const peerUrl = useMemo(() => {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:5173`;
  }, []);

  useEffect(() => {
    let alive = true;
    let inFlight = false;

    async function pollStatus() {
      if (inFlight) return;
      inFlight = true;
      try {
        const [res, modeRes] = await Promise.all([
          fetch(`${EDGE_API_BASE}/edge/status`, { headers: buildHeaders() }),
          fetch(`${API_BASE}/mode`, { headers: buildHeaders() }).catch(() => null),
        ]);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        const mData = modeRes && modeRes.ok ? await modeRes.json() : null;
        if (!alive) return;

        setEdge(data);
        if (mData) setModeState(mData);
        setLastSyncTs(Date.now() / 1000);
        setFetchError('');

        if (Date.now() > editingUntilRef.current) {
          setDraft({
            fps: Number(data.fps ?? 5),
            width: Number(data.width ?? 640),
            quality: Number(data.quality ?? 80),
            device_id: data.device_id || 'edge-01',
          });
        }
      } catch (err) {
        if (!alive) return;
        setFetchError(err instanceof Error ? err.message : 'Controller unreachable');
      } finally {
        inFlight = false;
      }
    }

    pollStatus();
    const timer = window.setInterval(pollStatus, POLL_STATUS_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
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
        const res = await fetch(`${EDGE_API_BASE}/edge/frame?t=${Date.now()}`, {
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
        // Keep last frame visible on transient polling stalls.
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

  function showNotice(tone, title, detail) {
    setNotice({ tone, title, detail, ts: Date.now() / 1000 });
  }

  useEffect(() => {
    if (!notice || notice.tone === 'crit') return undefined;
    const timer = window.setTimeout(() => {
      setNotice(null);
    }, 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function handleTabChange(nextTab) {
    setActiveTab(nextTab);
    setNotice((prev) => (prev?.tone === 'crit' ? prev : null));
  }

  async function patchConfig(payload, key, successTitle, successDetail) {
    setBusyKey(key);
    try {
      const res = await fetch(`${EDGE_API_BASE}/edge/config`, {
        method: 'POST',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => `HTTP ${res.status}`);
        throw new Error(errText || `HTTP ${res.status}`);
      }
      const updated = await res.json();
      setEdge(updated);
      setDraft({
        fps: Number(updated.fps ?? draft.fps),
        width: Number(updated.width ?? draft.width),
        quality: Number(updated.quality ?? draft.quality),
        device_id: updated.device_id || draft.device_id,
      });
      editingUntilRef.current = 0;
      if (successTitle) {
        showNotice('ok', successTitle, successDetail || updated.status_msg || '');
      }
    } catch (err) {
      showNotice(
        'crit',
        'Configuration update failed',
        err instanceof Error ? err.message : 'Request failed'
      );
    } finally {
      setBusyKey('');
    }
  }

  function handleSliderChange(field, value, label, unit) {
    const num = Number(value);
    editingUntilRef.current = Date.now() + 2000;
    setDraft((prev) => ({ ...prev, [field]: num }));

    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = window.setTimeout(() => {
      patchConfig(
        { [field]: num },
        `slider-${field}`,
        `Updated ${label}`,
        `Set to ${num}${unit}`
      );
    }, 180);
  }

  function handleCustomSourceSubmit(event) {
    event.preventDefault();
    const trimmed = customSource.trim();
    if (!trimmed) return;
    patchConfig(
      { source: trimmed },
      'custom-source',
      'Source switched',
      trimmed
    );
  }

  function handleSaveEncoder(event) {
    event.preventDefault();
    const cleanedDevice = draft.device_id.trim() || 'edge-01';
    patchConfig(
      {
        fps: Number(draft.fps),
        width: Number(draft.width),
        quality: Number(draft.quality),
        device_id: cleanedDevice,
      },
      'save-encoder',
      'Encoder profile saved',
      `${cleanedDevice} · ${draft.fps} FPS · ${draft.width}px · Q${draft.quality}`
    );
  }

  async function switchMode(nextMode, nextArming) {
    setBusyKey('mode-switch');
    try {
      const payload = { mode: nextMode };
      if (nextArming) payload.arming = nextArming;
      const res = await fetch(`${API_BASE}/mode`, {
        method: 'POST',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const updated = await res.json();
      setModeState(updated);
      showNotice(
        'ok',
        `Mode set to ${updated.mode.toUpperCase()}`,
        updated.mode === 'home' ? `Arming: ${updated.arming}` : 'Public space rules active'
      );
    } catch (err) {
      showNotice('crit', 'Mode switch failed', err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusyKey('');
    }
  }

  async function postSyntheticEvent(payload) {
    const res = await fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => `HTTP ${res.status}`);
      throw new Error(errText || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function triggerRule(spec) {
    const deviceId = edge?.device_id || draft.device_id || 'edge-01';
    const now = Date.now() / 1000;
    setBusyKey(`inject-${spec.key}`);

    try {
      if (modeState.mode !== spec.mode || (spec.arming && modeState.arming !== spec.arming)) {
        await switchMode(spec.mode, spec.arming);
      }
      const subId = spec.key === 'r1' ? deviceId : `${deviceId}-${spec.key}`;
      for (const ev of spec.events(now)) {
        await postSyntheticEvent({
          ts: now + ev.tsOffset,
          source: 'edge-deck',
          device_id: subId,
          object_class: ev.object_class,
          count: ev.count,
          avg_conf: ev.avg_conf,
          ...(ev.box ? { box: ev.box } : {}),
        });
      }
      showNotice('ok', `Synthetic ${spec.key.toUpperCase()} sent`, `${spec.title} posted for ${subId}`);
    } catch (err) {
      showNotice(
        'crit',
        `Synthetic ${spec.key.toUpperCase()} failed`,
        err instanceof Error ? err.message : 'Unable to post /events'
      );
    } finally {
      setBusyKey('');
    }
  }

  const availableSources = Array.isArray(edge?.available_sources)
    ? edge.available_sources
    : [];
  const knownSourceIds = new Set(availableSources.map((s) => String(s.id)));
  const isCustomActive = Boolean(edge?.source) && !knownSourceIds.has(String(edge.source));
  const dropdownSourceValue = showCustomInput || isCustomActive ? '__other__' : String(edge?.source || '');
  const activeClipRules = CLIP_RULE_HINTS[String(edge?.source || '')] || {
    mode: modeState.mode,
    rules: modeState.mode === 'home'
      ? ['H1 person_in_zone', 'H2 night_person', 'H3 loitering', 'H11 vehicle_in_driveway']
      : ['R1 occupancy_spike', 'R2 unexpected_object', 'R3 object_dwell'],
  };
  const activeDevice = edge?.device_id || draft.device_id;
  const statusTone = fetchError
    ? 'warn'
    : edge?.error_msg
      ? 'crit'
      : edge?.streaming
        ? 'live'
        : 'warn';

  const topMeta = fetchError
    ? 'Controller offline'
    : `${activeDevice} · ${edge?.streaming ? 'Streaming' : 'Paused'}`;

  const metrics = [
    {
      label: 'Active source',
      value: edge?.source_kind || '-',
      mono: true,
      title: edge?.source !== undefined ? String(edge.source) : '',
    },
    {
      label: 'Outbound FPS',
      value: (edge?.window_fps ?? 0).toFixed(1),
      unit: 'fps',
    },
    {
      label: 'Uplink bandwidth',
      value: (edge?.window_kbps ?? 0).toFixed(1),
      unit: 'kbps',
    },
    {
      label: 'Frame payload',
      value: (edge?.last_frame_kb ?? 0).toFixed(1),
      unit: 'KB',
    },
    {
      label: 'Frames emitted',
      value: edge?.frames_sent ?? 0,
    },
    {
      label: 'Server queue',
      value: edge?.server_queue_depth ?? 0,
      unit: '/ 3',
    },
  ];

  const tabs = [
    { id: 'sources', label: 'Video Source' },
    { id: 'encoder', label: 'Encoder' },
    { id: 'inject', label: 'Event Injector' },
  ];

  const subtitle = edge
    ? `${edge.source_kind || 'video'} emitter (${edge.device_id}) · ${edge.width}px JPEG at ${edge.quality}% · target ${edge.fps} FPS`
    : 'Configure video capture source, JPEG compression, and synthetic rule checks';

  const headerStamp = fetchError
    ? `Disconnected (${fetchError})`
    : lastSyncTs
      ? `Synced ${formatClock(lastSyncTs)}`
      : 'Connecting…';

  return (
    <div className="console-shell">
      <ConsoleTopBar
        title="Edge Control Deck"
        port="5174"
        statusTone={statusTone}
        metaText={topMeta}
        peerLabel="Analytics Console (:5173)"
        peerHref={peerUrl}
      />

      <ConsolePageHeader
        title="Edge Emitter Control"
        subtitle={subtitle}
        stamp={headerStamp}
      />

      {fetchError && (
        <div className="notice-bar notice-bar--warn" role="status">
          <div className="notice-main">
            <span className="notice-title">Controller unreachable</span>
            <span>
              Unable to reach {EDGE_API_BASE}/edge/status ({fetchError}). Retrying automatically.
            </span>
          </div>
        </div>
      )}

      {!fetchError && edge?.error_msg && (
        <div className="notice-bar notice-bar--crit" role="alert">
          <div className="notice-main">
            <span className="notice-title">Capture error</span>
            <span>{edge.error_msg}</span>
          </div>
        </div>
      )}

      {notice && (
        <div className={`notice-bar notice-bar--${notice.tone}`} role="status">
          <div className="notice-main">
            <span className="notice-title">{notice.title}</span>
            {notice.detail && <span>{notice.detail}</span>}
          </div>
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => setNotice(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <MetricStrip metrics={metrics} />

      <TabBar
        tabs={tabs}
        activeTab={activeTab}
        onChange={handleTabChange}
        ariaLabel="Edge Control sections"
      />

      {activeTab === 'sources' && (
        <section className="split-grid split-grid--equal" aria-labelledby="tab-sources">
          <article className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Video Source Switcher</h2>
              <button
                type="button"
                className={`btn btn--sm${edge?.streaming ? '' : ' btn--primary'}`}
                disabled={!edge || busyKey === 'toggle-stream'}
                onClick={() =>
                  patchConfig(
                    { streaming: !edge?.streaming },
                    'toggle-stream',
                    edge?.streaming ? 'Stream paused' : 'Stream resumed',
                    edge?.streaming
                      ? 'Edge frame emission paused'
                      : 'Resumed sending frames to server'
                  )
                }
              >
                {edge?.streaming ? 'Pause Stream' : 'Resume Stream'}
              </button>
            </div>

            <div className="form-group" style={{ marginBottom: '12px' }}>
              <label className="form-label" htmlFor="source-select">
                <span>Preset video source</span>
                <span className="form-hint">Pick a clip or Other for URL</span>
              </label>
              <select
                id="source-select"
                className="input"
                value={dropdownSourceValue}
                disabled={busyKey.startsWith('source-')}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '__other__') {
                    setShowCustomInput(true);
                  } else {
                    setShowCustomInput(false);
                    const picked = availableSources.find((s) => String(s.id) === val);
                    patchConfig(
                      { source: val },
                      `source-${val}`,
                      'Source switched',
                      picked?.label || val
                    );
                  }
                }}
              >
                {availableSources.map((src) => (
                  <option key={String(src.id)} value={String(src.id)}>
                    {src.label} [{src.tag || src.kind}]
                  </option>
                ))}
                <option value="__other__">Other (Custom URL / Path)…</option>
              </select>
            </div>

            {(showCustomInput || isCustomActive) && (
              <form className="form-group" style={{ marginBottom: '12px' }} onSubmit={handleCustomSourceSubmit}>
                <label className="form-label" htmlFor="custom-source-url">
                  <span>Custom stream URL or local path</span>
                  <span className="form-hint">RTSP / HTTP / YouTube / MP4</span>
                </label>
                <div className="input-row">
                  <input
                    id="custom-source-url"
                    type="text"
                    className="input input--mono"
                    placeholder="https://www.youtube.com/watch?v=... or rtsp://..."
                    value={customSource}
                    onChange={(e) => setCustomSource(e.target.value)}
                  />
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={!customSource.trim() || busyKey === 'custom-source'}
                  >
                    {busyKey === 'custom-source' ? 'Switching…' : 'Switch'}
                  </button>
                </div>
              </form>
            )}

            <hr className="divider-rule" />

            <div className="form-group">
              <div className="form-label">
                <span>Rule Engine Mode &amp; Arming</span>
                <span className="pill pill--ok">{modeState.mode.toUpperCase()}</span>
              </div>
              <div className="input-row">
                <button
                  type="button"
                  className={`btn btn--sm${modeState.mode === 'home' ? ' btn--primary' : ''}`}
                  disabled={busyKey === 'mode-switch'}
                  onClick={() => switchMode('home', modeState.arming)}
                >
                  Home Security
                </button>
                <button
                  type="button"
                  className={`btn btn--sm${modeState.mode === 'public' ? ' btn--primary' : ''}`}
                  disabled={busyKey === 'mode-switch'}
                  onClick={() => switchMode('public')}
                >
                  Public Space
                </button>
                {modeState.mode === 'home' && (
                  <select
                    aria-label="Home arming state"
                    className="input"
                    value={modeState.arming || 'armed_night'}
                    disabled={busyKey === 'mode-switch'}
                    onChange={(e) => switchMode('home', e.target.value)}
                  >
                    <option value="armed_night">armed_night</option>
                    <option value="armed_away">armed_away</option>
                    <option value="armed_home">armed_home</option>
                    <option value="disarmed">disarmed</option>
                  </select>
                )}
              </div>
              <div className="form-hint">
                Rules for current feed ({activeClipRules.mode} recommended):{' '}
                <span className="mono">{activeClipRules.rules.join(' · ')}</span>
              </div>
              {activeClipRules.mode !== modeState.mode && (
                <div>
                  <button
                    type="button"
                    className="btn btn--sm"
                    disabled={busyKey === 'mode-switch'}
                    onClick={() => switchMode(activeClipRules.mode, activeClipRules.mode === 'home' ? 'armed_night' : undefined)}
                  >
                    Apply recommended {activeClipRules.mode.toUpperCase()} mode
                  </button>
                </div>
              )}
              {edge?.status_msg && (
                <div className="form-hint">{edge.status_msg}</div>
              )}
            </div>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Raw Outbound Frame</h2>
              <span className="panel-meta">
                {!edge?.streaming
                  ? 'Paused'
                  : (edge?.frames_sent ?? 0) > 0
                    ? `Transmitting · ${(edge?.last_frame_kb ?? 0).toFixed(1)} KB`
                    : 'Initializing'}
              </span>
            </div>

            <div className="video-stage">
              {frameUrl ? (
                <img
                  className="video-frame"
                  src={frameUrl}
                  alt="Raw edge camera capture preview"
                />
              ) : (
                <div className="video-empty">
                  <div>Waiting for raw capture preview</div>
                  <div className="video-empty-sub">
                    Stream preview activates once capture emits frames to /edge/frame
                  </div>
                </div>
              )}
            </div>

            <div className="video-caption">
              <span className="mono">
                {edge?.source !== undefined ? String(edge.source) : '-'}
              </span>
              <span className="mono">
                {edge?.fps ?? draft.fps} FPS target · {edge?.width ?? draft.width}px
              </span>
            </div>
          </article>
        </section>
      )}

      {activeTab === 'encoder' && (
        <section
          className="split-grid split-grid--equal"
          aria-labelledby="tab-encoder"
        >
          <article className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Encoder &amp; Bandwidth Settings</h2>
              <span className="panel-meta">Applies live over HTTP</span>
            </div>

            <form className="stack-col" onSubmit={handleSaveEncoder}>
              <div className="form-group">
                <label className="form-label" htmlFor="encoder-fps">
                  <span>Target capture rate</span>
                  <span className="mono">{draft.fps} FPS</span>
                </label>
                <input
                  id="encoder-fps"
                  type="range"
                  className="range-input"
                  min={1}
                  max={30}
                  step={1}
                  value={draft.fps}
                  onChange={(e) =>
                    handleSliderChange('fps', e.target.value, 'capture rate', ' FPS')
                  }
                />
                <div className="range-scale">
                  <span>1 FPS</span>
                  <span>15 FPS</span>
                  <span>30 FPS</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="encoder-width">
                  <span>Resize width</span>
                  <span className="mono">{draft.width} px</span>
                </label>
                <input
                  id="encoder-width"
                  type="range"
                  className="range-input"
                  min={320}
                  max={1280}
                  step={64}
                  value={draft.width}
                  onChange={(e) =>
                    handleSliderChange('width', e.target.value, 'resize width', ' px')
                  }
                />
                <div className="range-scale">
                  <span>320 px</span>
                  <span>800 px</span>
                  <span>1280 px</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="encoder-quality">
                  <span>JPEG quality</span>
                  <span className="mono">{draft.quality}%</span>
                </label>
                <input
                  id="encoder-quality"
                  type="range"
                  className="range-input"
                  min={30}
                  max={95}
                  step={5}
                  value={draft.quality}
                  onChange={(e) =>
                    handleSliderChange('quality', e.target.value, 'JPEG quality', '%')
                  }
                />
                <div className="range-scale">
                  <span>30%</span>
                  <span>95%</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="encoder-device-id">
                  <span>Edge device ID</span>
                  <span className="form-hint">Tag attached to emitted frames</span>
                </label>
                <div className="input-row">
                  <input
                    id="encoder-device-id"
                    type="text"
                    className="input input--mono"
                    value={draft.device_id}
                    onFocus={() => {
                      editingUntilRef.current = Date.now() + 10000;
                    }}
                    onChange={(e) => {
                      editingUntilRef.current = Date.now() + 10000;
                      setDraft((prev) => ({ ...prev, device_id: e.target.value }));
                    }}
                  />
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={busyKey === 'save-encoder'}
                  >
                    {busyKey === 'save-encoder' ? 'Saving…' : 'Save Settings'}
                  </button>
                </div>
              </div>
            </form>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Effective Emitter Profile</h2>
              <span className={`pill pill--${edge?.streaming ? 'ok' : 'warning'}`}>
                {edge?.streaming ? 'Streaming' : 'Paused'}
              </span>
            </div>

            <div className="kv-list">
              <div className="kv-row">
                <span className="kv-key">Configured device ID</span>
                <span className="kv-val">{edge?.device_id || '-'}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Active source</span>
                <span className="kv-val">
                  {edge?.source !== undefined ? String(edge.source) : '-'}
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Target vs measured FPS</span>
                <span className="kv-val">
                  {edge?.fps ?? '-'} target / {(edge?.window_fps ?? 0).toFixed(1)} actual
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Output frame width</span>
                <span className="kv-val">{edge?.width ?? '-'} px</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">JPEG quality factor</span>
                <span className="kv-val">{edge?.quality ?? '-'}%</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Average payload size</span>
                <span className="kv-val">{(edge?.last_frame_kb ?? 0).toFixed(1)} KB</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Sustained uplink rate</span>
                <span className="kv-val">{(edge?.window_kbps ?? 0).toFixed(1)} kbps</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Server ingest queue</span>
                <span className="kv-val">{edge?.server_queue_depth ?? 0} / 3 slots</span>
              </div>
            </div>
          </article>
        </section>
      )}

      {activeTab === 'inject' && (
        <section className="tri-grid" aria-labelledby="tab-inject">
          {SYNTHETIC_TRIGGERS.map((spec) => {
            const pillCls =
              spec.sev === 'critical' ? 'pill--critical' : spec.sev === 'warning' ? 'pill--warning' : 'pill--info';
            return (
              <article key={spec.key} className="panel">
                <div className="panel-head">
                  <h2 className="panel-title">{spec.title}</h2>
                  <span className={`pill ${pillCls}`}>{spec.mode} · {spec.sev}</span>
                </div>
                <p className="card-desc">{spec.desc}</p>
                <div className="code-summary">
                  {spec.meta}
                  <br />
                  device_id: &quot;{spec.key === 'r1' ? activeDevice : `${activeDevice}-${spec.key}`}&quot;
                </div>
                <div className="card-spacer" />
                <button
                  type="button"
                  className={`btn btn--full${spec.sev === 'critical' ? ' btn--danger' : ''}`}
                  disabled={busyKey === `inject-${spec.key}`}
                  onClick={() => triggerRule(spec)}
                >
                  {busyKey === `inject-${spec.key}` ? `Sending ${spec.key.toUpperCase()}…` : spec.btn}
                </button>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}
