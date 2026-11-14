import React, { useEffect, useRef, useState } from 'react';

/**
 * Render a custom cursor dot + spring-eased trailing ring that enlarges over interactive elements.
 */
export function CustomCursor() {
  const dotRef = useRef(null);
  const ringRef = useRef(null);

  useEffect(() => {
    let mx = -100, my = -100;
    let rx = -100, ry = -100;
    let rafId;

    /** Track raw mouse coordinates and toggle hover styling over clickable controls. */
    const onMove = (e) => {
      mx = e.clientX;
      my = e.clientY;
      if (dotRef.current) {
        dotRef.current.style.left = `${mx}px`;
        dotRef.current.style.top = `${my}px`;
      }
      const target = e.target;
      const isInteractive =
        target &&
        target.closest('button, a, input, select, [data-interactive="true"], .source-item');
      if (ringRef.current) {
        ringRef.current.classList.toggle('is-hover', Boolean(isInteractive));
      }
    };

    /** Smoothly interpolate the trailing ring toward the pointer position on each animation frame. */
    const tick = () => {
      rx += (mx - rx) * 0.24;
      ry += (my - ry) * 0.24;
      if (ringRef.current) {
        ringRef.current.style.left = `${rx}px`;
        ringRef.current.style.top = `${ry}px`;
      }
      rafId = requestAnimationFrame(tick);
    };

    window.addEventListener('mousemove', onMove, { passive: true });
    rafId = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <>
      <div ref={ringRef} className="custom-cursor-ring" />
      <div ref={dotRef} className="custom-cursor-dot" />
    </>
  );
}

/**
 * Render an animated pill tab switcher whose sliding highlight tracks the active button width/offset.
 */
export function AnimatedTabBar({ tabs, activeTab, onChange }) {
  const barRef = useRef(null);
  const btnRefs = useRef({});
  const [sliderStyle, setSliderStyle] = useState({ width: 0, transform: 'translateX(0px)' });

  useEffect(() => {
    /** Measure the active tab button relative to the bar container and reposition the pill slider. */
    const updateSlider = () => {
      const btn = btnRefs.current[activeTab];
      const bar = barRef.current;
      if (btn && bar) {
        const barRect = bar.getBoundingClientRect();
        const btnRect = btn.getBoundingClientRect();
        // Subtract 6px container padding so the slider aligns flush with the button slot
        const offsetLeft = btnRect.left - barRect.left - 6;
        setSliderStyle({
          width: `${btnRect.width}px`,
          transform: `translateX(${offsetLeft}px)`,
        });
      }
    };
    updateSlider();
    window.addEventListener('resize', updateSlider);
    return () => window.removeEventListener('resize', updateSlider);
  }, [activeTab, tabs]);

  return (
    <div className="ios-tabbar-wrap">
      <div
        ref={barRef}
        className="ios-tabbar"
        style={{ gridTemplateColumns: `repeat(${tabs.length}, auto)` }}
      >
        <div className="ios-tab-slider" style={sliderStyle} />
        {tabs.map((t) => (
          <button
            key={t.id}
            ref={(el) => (btnRefs.current[t.id] = el)}
            className={`ios-tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => onChange(t.id)}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Top frosted-glass console header showing console role badge, title, subtitle, and peer UI link.
 */
export function HeroHeader({ badge, title, subtitle, peerUrl, peerLabel }) {
  return (
    <header className="hero-bar">
      <div>
        <div className="role-pill">
          <span className="pulse-dot" />
          <span>{badge}</span>
        </div>
        <h1 className="hero-title">{title}</h1>
        <p className="hero-subtitle">{subtitle}</p>
      </div>
      <a className="peer-switch-btn" href={peerUrl} target="_blank" rel="noreferrer">
        <span>{peerLabel}</span>
        <span>↗</span>
      </a>
    </header>
  );
}
