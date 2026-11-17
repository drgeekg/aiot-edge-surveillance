import React from 'react';

/** Base FastAPI backend URL resolved from environment with local default. */
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Build request headers, attaching the configured X-API-Key when present.
 * @param {Record<string, string>} extra Optional extra headers to merge.
 * @returns {Record<string, string>} Merged headers dictionary.
 */
export function buildHeaders(extra = {}) {
  const apiKey = import.meta.env.VITE_API_KEY;
  return apiKey ? { ...extra, 'X-API-Key': apiKey } : { ...extra };
}

/**
 * Format a Unix timestamp in seconds as HH:MM:SS local time.
 * @param {number|null|undefined} tsSeconds Epoch seconds.
 * @returns {string} Formatted timestamp or em dash when missing.
 */
export function formatClock(tsSeconds) {
  if (!tsSeconds || Number.isNaN(Number(tsSeconds))) return '-';
  const d = new Date(Number(tsSeconds) * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/**
 * Format elapsed seconds into compact duration (e.g. 42s, 5m 12s, 1h 04m).
 * @param {number|null|undefined} seconds Elapsed seconds.
 * @returns {string} Formatted duration or em dash when missing.
 */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) {
    return '-';
  }
  const s = Math.max(0, Math.floor(Number(seconds)));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const remS = s % 60;
  if (m < 60) return `${m}m ${String(remS).padStart(2, '0')}s`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return `${h}h ${String(remM).padStart(2, '0')}m`;
}

/**
 * Compact 48px matte navigation bar shared across Analytics (:5173) and Edge (:5174).
 */
export function ConsoleTopBar({
  title,
  port,
  statusTone = 'live',
  metaText,
  peerLabel,
  peerHref,
}) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className={`status-dot status-dot--${statusTone}`} aria-hidden="true" />
        <span className="brand-name">{title}</span>
        {port && <span className="brand-port">:{port}</span>}
      </div>

      <div className="topbar-right">
        {metaText && <span className="topbar-meta">{metaText}</span>}
        {peerLabel && peerHref && (
          <a className="topbar-link" href={peerHref}>
            <span>{peerLabel}</span>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M5 11L11 5M11 5H6M11 5V10"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        )}
      </div>
    </header>
  );
}

/**
 * Quiet page title, one-line summary, and freshness timestamp row.
 */
export function ConsolePageHeader({ title, subtitle, stamp }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      {stamp && <div className="page-stamp">{stamp}</div>}
    </div>
  );
}

/**
 * Unified 6-cell hairline-divided telemetry strip.
 */
export function MetricStrip({ metrics }) {
  return (
    <section className="metric-strip" aria-label="Key telemetry metrics">
      {metrics.map((item) => (
        <div className="metric-cell" key={item.label}>
          <div className="metric-label">{item.label}</div>
          <div
            className={`metric-value${item.mono ? ' metric-value--mono' : ''}`}
            title={item.title || undefined}
          >
            <span>{item.value}</span>
            {item.unit && <span className="metric-unit">{item.unit}</span>}
          </div>
        </div>
      ))}
    </section>
  );
}

/**
 * Accessible underline tab navigation strip.
 */
export function TabBar({ tabs, activeTab, onChange, ariaLabel = 'Console views' }) {
  return (
    <nav className="tab-bar" role="tablist" aria-label={ariaLabel}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={isActive}
            className="tab-btn"
            onClick={() => onChange(tab.id)}
          >
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge !== null && tab.badge !== '' && (
              <span className={`tab-badge${tab.badgeAlert ? ' tab-badge--alert' : ''}`}>
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
