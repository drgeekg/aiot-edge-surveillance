import os
import subprocess
from PIL import Image, ImageChops

FIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(FIG_DIR, exist_ok=True)

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
EDGE_BIN = next(p for p in EDGE_PATHS if os.path.exists(p))

# Clean academic styling matching the previous case-study report:
# - Pure white background, 1px solid #333 outer frame, zero pill badges, zero emojis
# - Two-tone palette: Accent Blue (#2563eb / #dbeafe) and Muted Stone (#c4c4b8 / #f4f4f0)
# - Crimson (#be123c) used only where critical/escalation distinction is plotted
COMMON_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #ffffff;
  font-family: 'Times New Roman', Georgia, serif;
  color: #111111;
  padding: 16px;
  -webkit-font-smoothing: antialiased;
}
.frame {
  width: 1120px;
  border: 1.2px solid #222222;
  background: #ffffff;
  padding: 22px 26px;
}
.caption-top {
  font-size: 13px;
  color: #444444;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #d4d4d4;
  padding-bottom: 6px;
}
code {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 0.92em;
}
"""

# ---------------------------------------------------------------------------
# FIG 1: Three-lane swimlane architecture diagram (matching Fig 5 of previous report)
# ---------------------------------------------------------------------------
FIG1_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.lane {{
  display: grid;
  grid-template-columns: 195px 1fr;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px dashed #999999;
}}
.lane:last-child {{ border-bottom: none; padding-bottom: 4px; }}
.lane-title {{ font-size: 16px; font-weight: bold; color: #111; margin-bottom: 3px; }}
.lane-sub {{ font-size: 12.5px; color: #444; line-height: 1.35; }}
.flow {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}}
.node {{
  flex: 1;
  border: 1px solid #555555;
  border-radius: 5px;
  background: #ffffff;
  padding: 11px 12px;
  text-align: center;
  min-height: 68px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}
.node.ai {{
  border: 1.8px solid #2563eb;
  background: #e8f0fe;
}}
.node.muted {{
  background: #f5f5f2;
  border-style: dashed;
}}
.node-title {{ font-size: 14.5px; font-weight: bold; margin-bottom: 3px; }}
.node-sub {{ font-size: 12px; color: #333; line-height: 1.3; }}
.arrow {{
  font-size: 12px;
  color: #333;
  text-align: center;
  min-width: 72px;
}}
.arrow-line {{
  border-top: 1.4px solid #333;
  position: relative;
  margin: 4px 0;
}}
.arrow-line::after {{
  content: '';
  position: absolute;
  right: -1px;
  top: -4.5px;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-left: 7px solid #333;
}}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Blue box = where computer vision or language-model reasoning runs</span>
    <span>Two-process HTTP split (<code>:8001</code> &rarr; <code>:8000</code>)</span>
  </div>

  <div class="lane">
    <div>
      <div class="lane-title">1. IoT Edge Tier</div>
      <div class="lane-sub">Simulated camera server<br>Port <code>:8001</code> &amp; UI <code>:5174</code></div>
    </div>
    <div class="flow">
      <div class="node muted">
        <div class="node-title">Video Sources</div>
        <div class="node-sub">11 MP4 clips, webcam,<br>RTSP / YouTube</div>
      </div>
      <div class="arrow"><div>OpenCV read</div><div class="arrow-line"></div><div>5 FPS loop</div></div>
      <div class="node">
        <div class="node-title">Simulated Edge Node</div>
        <div class="node-sub"><code>edge.edge_server</code> (<code>:8001</code>)<br>Resize 960px, JPEG q=90</div>
      </div>
      <div class="arrow"><div>HTTP POST</div><div class="arrow-line"></div><div><code>/frames</code></div></div>
      <div class="node">
        <div class="node-title">Edge Control Deck</div>
        <div class="node-sub">React console (<code>:5174</code>)<br>Source, encoder &amp; mode</div>
      </div>
    </div>
  </div>

  <div class="lane">
    <div>
      <div class="lane-title">2. Analysis Server</div>
      <div class="lane-sub">Local vision &amp; storage<br>Port <code>:8000</code> &amp; UI <code>:5173</code></div>
    </div>
    <div class="flow">
      <div class="node">
        <div class="node-title">Bounded Ingest Queue</div>
        <div class="node-sub"><code>server.app</code> (<code>:8000</code>)<br>8 slots, drop-oldest</div>
      </div>
      <div class="arrow"><div>cv-worker</div><div class="arrow-line"></div><div>640&times;640</div></div>
      <div class="node ai">
        <div class="node-title">YOLO26n ONNX + Tracker</div>
        <div class="node-sub">Local CPU inference (27.6 ms)<br>Hysteresis 0.40/0.30, IoU track</div>
      </div>
      <div class="arrow"><div>Tracks</div><div class="arrow-line"></div><div>Polygons</div></div>
      <div class="node ai">
        <div class="node-title">Dual-Mode Rule Engine</div>
        <div class="node-sub">Home (H1–H18) &amp; Public (P1–P21)<br>+ SQLite WAL &amp; Console <code>:5173</code></div>
      </div>
    </div>
  </div>

  <div class="lane">
    <div>
      <div class="lane-title">3. Triage &amp; Alerting</div>
      <div class="lane-sub">Text-only cloud LLM<br>&amp; Hermes gateway <code>:8644</code></div>
    </div>
    <div class="flow">
      <div class="node ai">
        <div class="node-title">LangGraph Triage Agent</div>
        <div class="node-sub">NVIDIA Nemotron-3-Ultra<br>Text metadata only; fail-open</div>
      </div>
      <div class="arrow"><div>Confirmed</div><div class="arrow-line"></div><div>HMAC-SHA256</div></div>
      <div class="node">
        <div class="node-title">Hermes Gateway</div>
        <div class="node-sub">Webhook listener (<code>:8644</code>)<br><code>deliver_only: true</code></div>
      </div>
      <div class="arrow"><div>Bot API</div><div class="arrow-line"></div><div>HTTPS</div></div>
      <div class="node muted">
        <div class="node-title">Telegram Phone Alert</div>
        <div class="node-sub">Structured alert card with<br>zone, time &amp; agent reason</div>
      </div>
    </div>
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 2: Staged pipeline diagram (matching Fig 6 of previous report)
# ---------------------------------------------------------------------------
FIG2_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.stages {{
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}}
.stage-card {{
  border: 1px solid #666666;
  border-radius: 5px;
  padding: 14px 13px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 175px;
}}
.stage-card.ai {{
  border: 1.8px solid #2563eb;
  background: #e8f0fe;
}}
.st-head {{ font-size: 15px; font-weight: bold; margin-bottom: 6px; }}
.st-body {{ font-size: 12.5px; color: #222; line-height: 1.42; margin-bottom: 12px; }}
.st-meta {{ font-size: 11px; color: #555; border-top: 1px solid #ccc; padding-top: 6px; }}
.st-meta b {{ display: block; color: #111; font-size: 12px; }}
.footer-bar {{
  border: 1px solid #666666;
  border-radius: 5px;
  background: #f4f4f0;
  padding: 10px 16px;
  text-align: center;
  font-size: 13.5px;
}}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>End-to-end life of one video frame from edge capture to mobile notification</span>
    <span>Stages 1–2 on Edge (<code>:8001</code>) &middot; Stages 3–5 on Server (<code>:8000</code>)</span>
  </div>
  <div class="stages">
    <div class="stage-card">
      <div>
        <div class="st-head">Stage 1: Capture &amp; Encode</div>
        <div class="st-body"><code>VideoSource</code> reads frame, resizes to 960 px width, encodes JPEG at quality 90 (~96.2 KB).</div>
      </div>
      <div class="st-meta">Process<b>Edge Node (<code>:8001</code>)</b></div>
    </div>
    <div class="stage-card">
      <div>
        <div class="st-head">Stage 2: Ingest &amp; Queue</div>
        <div class="st-body"><code>POST /frames</code> validates headers &amp; magic bytes; pushes to 8-slot drop-oldest queue.</div>
      </div>
      <div class="st-meta">Process<b>FastAPI Ingest (<code>:8000</code>)</b></div>
    </div>
    <div class="stage-card ai">
      <div>
        <div class="st-head">Stage 3: Detect &amp; Track</div>
        <div class="st-body">Letterbox 640&times;640, run NMS-free <code>YOLO26n</code> ONNX, match IoU + centroid tracks.</div>
      </div>
      <div class="st-meta">Vision Stage<b>ONNX Runtime + Tracker</b></div>
    </div>
    <div class="stage-card ai">
      <div>
        <div class="st-head">Stage 4: Rules &amp; Triage</div>
        <div class="st-body">Evaluate Home/Public rules &amp; S5 escalation; async LangGraph LLM triage on text metadata.</div>
      </div>
      <div class="st-meta">Decision Stage<b>RuleEngine + LangGraph</b></div>
    </div>
    <div class="stage-card">
      <div>
        <div class="st-head">Stage 5: Store &amp; Deliver</div>
        <div class="st-body">Write SQLite WAL record; sign <code>HMAC-SHA256</code> webhook to Hermes (<code>:8644</code>) &rarr; Telegram.</div>
      </div>
      <div class="st-meta">Output Stage<b>SQLite + Hermes + UI</b></div>
    </div>
  </div>
  <div class="footer-bar">
    <b>Privacy &amp; Safety Invariant:</b> Raw video frames never leave the local host; if the cloud LLM times out, Stage 4 fails open so the alert is still delivered.
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 3: Clean LangGraph 4-Node State Machine
# ---------------------------------------------------------------------------
FIG3_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.grid-flow {{
  display: grid;
  grid-template-columns: 230px 45px 250px 65px 250px;
  align-items: center;
  justify-content: center;
  margin: 10px 0 16px 0;
}}
.box {{
  border: 1.2px solid #444;
  border-radius: 5px;
  padding: 12px 14px;
  background: #fff;
  text-align: left;
}}
.box.ai {{
  border: 1.8px solid #2563eb;
  background: #e8f0fe;
}}
.box.sup {{
  background: #f4f4f0;
  border-style: dashed;
}}
.b-title {{ font-size: 14.5px; font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.12); padding-bottom: 3px; }}
.b-text {{ font-size: 12px; color: #222; line-height: 1.38; }}
.branch-col {{ display: flex; flex-direction: column; gap: 14px; }}
.rule-strip {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  border-top: 1px solid #ccc;
  padding-top: 12px;
  font-size: 12px;
}}
.rule-item {{ background: #f8f8f6; border: 1px solid #bbb; padding: 8px 10px; border-radius: 4px; }}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Four-node LangGraph triage workflow (<code>server/agent.py</code>)</span>
    <span>Executed asynchronously in 2-worker background thread pool</span>
  </div>
  <div class="grid-flow">
    <div class="box">
      <div class="b-title">1. context_node</div>
      <div class="b-text">Collects rule name, zone, mode, arming state, local clock, and last 5 SQLite event summaries.<br><b>Zero pixel data included.</b></div>
    </div>
    <div style="text-align:center; font-size:18px;">&rarr;</div>
    <div class="box ai">
      <div class="b-title">2. decide_node (LLM)</div>
      <div class="b-text">Calls NVIDIA Cloud (<code>nemotron-3-ultra-550b</code>, 20s timeout). Parses JSON:<br><code>{{"real": bool, "severity": str, "reason": str}}</code></div>
    </div>
    <div style="text-align:center; font-size:12px; line-height:2.8;">
      <div><code>real=true</code> &rarr;</div>
      <div><code>real=false</code> &rarr;</div>
    </div>
    <div class="branch-col">
      <div class="box ai">
        <div class="b-title">3a. notify_node</div>
        <div class="b-text">Persists anomaly + LLM reason to SQLite; triggers console border, beep &amp; signed Hermes webhook.</div>
      </div>
      <div class="box sup">
        <div class="b-title">3b. suppress_node</div>
        <div class="b-text">Logs anomaly in SQLite with <code>[SUPPRESSED]</code> prefix for auditability; skips phone push.</div>
      </div>
    </div>
  </div>
  <div class="rule-strip">
    <div class="rule-item"><b>Policy: <code>always_alert</code></b><br>Rules S1, S2, H8, H9, H18, P5, P9, P11, P13 force <code>real = true</code>; LLM cannot suppress.</div>
    <div class="rule-item"><b>Policy: <code>review</code></b><br>Standard Home/Public detections; LLM evaluates context and may route to <code>suppress_node</code>.</div>
    <div class="rule-item"><b>Policy: <code>log_only</code> &amp; Fail-Open</b><br><code>log_only</code> rules (H4, H11, H17) bypass LLM; any LLM timeout routes to <code>notify_node</code>.</div>
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 4: Clean Architectural Geometry Diagram for Home & Public Zones
# ---------------------------------------------------------------------------
FIG4_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }}
.col-hdr {{ font-size: 14.5px; font-weight: bold; margin-bottom: 6px; display: flex; justify-content: space-between; }}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Normalised camera-frame polygon zones and directional tripwires in <code>config.yaml</code></span>
    <span>Coordinates in [0, 1] &times; [0, 1] evaluated on track foot-point <code>((x1+x2)/2, y2)</code></span>
  </div>
  <div class="two-col">
    <div>
      <div class="col-hdr"><span>A. Home Security Mode (Rules H1–H18)</span><span style="font-weight:normal;font-size:12px;color:#444;">4 Arming States</span></div>
      <svg width="510" height="250" viewBox="0 0 510 250" style="border:1px solid #444; background:#fafafa;">
        <!-- Grid lines -->
        <line x1="0" y1="62" x2="510" y2="62" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="0" y1="125" x2="510" y2="125" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="0" y1="187" x2="510" y2="187" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="127" y1="0" x2="127" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="255" y1="0" x2="255" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="382" y1="0" x2="382" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>

        <!-- fence_line -->
        <rect x="12" y="10" width="486" height="44" fill="#f4f4f0" stroke="#444" stroke-width="1.3"/>
        <text x="255" y="29" text-anchor="middle" font-size="12" font-weight="bold">fence_line (Perimeter &middot; H14)</text>
        <text x="255" y="44" text-anchor="middle" font-size="10.5" fill="#444">min 2s &middot; loiter 15s &middot; warning</text>

        <!-- Tripwire -->
        <line x1="16" y1="82" x2="176" y2="82" stroke="#2563eb" stroke-width="2" stroke-dasharray="5,3"/>
        <text x="96" y="75" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#2563eb">entry_line tripwire (H4)</text>

        <!-- door -->
        <rect x="18" y="92" width="155" height="145" fill="#e8f0fe" stroke="#2563eb" stroke-width="1.6"/>
        <text x="95" y="152" text-anchor="middle" font-size="12" font-weight="bold">door (Entry &middot; H1/H6)</text>
        <text x="95" y="168" text-anchor="middle" font-size="10.5" fill="#333">min 2s &middot; loiter 20s</text>
        <text x="95" y="183" text-anchor="middle" font-size="10.5" fill="#333">parcel left/taken check</text>

        <!-- yard -->
        <rect x="186" y="120" width="110" height="117" fill="#f4f4f0" stroke="#555" stroke-width="1.3"/>
        <text x="241" y="172" text-anchor="middle" font-size="12" font-weight="bold">yard (Exterior)</text>
        <text x="241" y="187" text-anchor="middle" font-size="10.5" fill="#444">min 3s &middot; loiter 60s</text>

        <!-- window -->
        <rect x="308" y="66" width="190" height="88" fill="#e8f0fe" stroke="#2563eb" stroke-width="1.6"/>
        <text x="403" y="106" text-anchor="middle" font-size="12" font-weight="bold">window (Interior &middot; H1)</text>
        <text x="403" y="122" text-anchor="middle" font-size="10.5" fill="#333">min 2s &middot; critical in armed_night</text>

        <!-- driveway -->
        <rect x="308" y="164" width="112" height="73" fill="#f4f4f0" stroke="#555" stroke-width="1.3"/>
        <text x="364" y="196" text-anchor="middle" font-size="11.5" font-weight="bold">driveway (H11)</text>
        <text x="364" y="211" text-anchor="middle" font-size="10" fill="#444">vehicles &middot; log_only</text>

        <!-- pool -->
        <rect x="428" y="164" width="70" height="73" fill="#fde8e8" stroke="#be123c" stroke-width="1.5"/>
        <text x="463" y="196" text-anchor="middle" font-size="11.5" font-weight="bold" fill="#991b1b">pool (H18)</text>
        <text x="463" y="211" text-anchor="middle" font-size="10" fill="#991b1b">hazard &middot; 1s</text>
      </svg>
    </div>

    <div>
      <div class="col-hdr"><span>B. Public Space Mode (Rules P1–P21)</span><span style="font-weight:normal;font-size:12px;color:#444;">Crowd &amp; Baggage</span></div>
      <svg width="510" height="250" viewBox="0 0 510 250" style="border:1px solid #444; background:#fafafa;">
        <line x1="0" y1="62" x2="510" y2="62" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="0" y1="125" x2="510" y2="125" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="0" y1="187" x2="510" y2="187" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="127" y1="0" x2="127" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="255" y1="0" x2="255" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>
        <line x1="382" y1="0" x2="382" y2="250" stroke="#e0e0e0" stroke-dasharray="3,3"/>

        <!-- queue -->
        <rect x="16" y="16" width="165" height="115" fill="#f4f4f0" stroke="#555" stroke-width="1.3"/>
        <text x="98" y="68" text-anchor="middle" font-size="12" font-weight="bold">queue (P18)</text>
        <text x="98" y="84" text-anchor="middle" font-size="10.5" fill="#444">max 5 persons &middot; wait 60s</text>

        <!-- corridor tripwire -->
        <line x1="195" y1="26" x2="335" y2="62" stroke="#2563eb" stroke-width="2" stroke-dasharray="5,3"/>
        <text x="265" y="34" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#2563eb">corridor tripwire &rarr; (P6/P19)</text>

        <!-- no_wheels -->
        <rect x="195" y="80" width="145" height="51" fill="#f4f4f0" stroke="#555" stroke-width="1.3"/>
        <text x="267" y="103" text-anchor="middle" font-size="11.5" font-weight="bold">no_wheels (P15)</text>
        <text x="267" y="118" text-anchor="middle" font-size="10" fill="#444">bicycle / motorcycle / skate</text>

        <!-- restricted -->
        <rect x="354" y="16" width="140" height="115" fill="#fde8e8" stroke="#be123c" stroke-width="1.5"/>
        <text x="424" y="66" text-anchor="middle" font-size="12" font-weight="bold" fill="#991b1b">restricted (P5)</text>
        <text x="424" y="82" text-anchor="middle" font-size="10.5" fill="#991b1b">min 2s &middot; always_alert</text>

        <!-- pedestrian -->
        <rect x="16" y="145" width="324" height="92" fill="#e8f0fe" stroke="#2563eb" stroke-width="1.6"/>
        <text x="178" y="184" text-anchor="middle" font-size="12" font-weight="bold">pedestrian concourse (P7 Crowd &le;6 &middot; P13 No Vehicles)</text>
        <text x="178" y="201" text-anchor="middle" font-size="10.5" fill="#333">P2/P3/P4 unattended bag dwell (&ge;30s) &amp; owner radius 0.20</text>

        <!-- no_parking -->
        <rect x="354" y="145" width="140" height="92" fill="#f4f4f0" stroke="#777" stroke-width="1.2" stroke-dasharray="4,3"/>
        <text x="424" y="186" text-anchor="middle" font-size="11.5" font-weight="bold" fill="#444">no_parking (P14)</text>
        <text x="424" y="202" text-anchor="middle" font-size="10" fill="#555">configured (300s limit)</text>
      </svg>
    </div>
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 5: Scientific Bar Charts for Payload & Latency (matching Figs 1 & 2 of previous report)
# ---------------------------------------------------------------------------
FIG5_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 26px; }}
.chart-title {{ font-size: 14px; font-weight: bold; margin-bottom: 10px; text-align: center; }}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Measured uplink payload footprint and processing latency on Intel Core i5-12500H</span>
    <span>Blue = active Edge JPEG / isolated pipeline &middot; Grey = baseline / contended full-stack load</span>
  </div>
  <div class="two-col">
    <div>
      <div class="chart-title">A. Per-Frame Uplink Payload by Ingestion Mode (KB)</div>
      <svg width="505" height="235" viewBox="0 0 505 235">
        <line x1="155" y1="15" x2="155" y2="195" stroke="#333" stroke-width="1.2"/>
        <line x1="155" y1="195" x2="485" y2="195" stroke="#333" stroke-width="1.2"/>
        <!-- Grid lines -->
        <line x1="255" y1="15" x2="255" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="355" y1="15" x2="355" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="455" y1="15" x2="455" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>

        <!-- Row 1: Raw BGR -->
        <text x="147" y="44" text-anchor="end" font-size="12.5" font-weight="bold">Raw BGR (640&times;480)</text>
        <rect x="155" y="27" width="280" height="24" fill="#c4c4b8" stroke="#777" stroke-width="0.8"/>
        <text x="442" y="44" font-size="12" font-weight="bold">900.0 KB</text>

        <!-- Row 2: Live JPEG q=90 -->
        <text x="147" y="88" text-anchor="end" font-size="12.5" font-weight="bold">Edge JPEG (960px, q=90)</text>
        <rect x="155" y="71" width="68" height="24" fill="#2563eb"/>
        <text x="230" y="88" font-size="12" font-weight="bold" fill="#1e40af">96.2 KB (-89.3%)</text>

        <!-- Row 3: Bench JPEG q=70 -->
        <text x="147" y="132" text-anchor="end" font-size="12.5" font-weight="bold">Edge JPEG (640px, q=70)</text>
        <rect x="155" y="115" width="32" height="24" fill="#2563eb"/>
        <text x="194" y="132" font-size="12" font-weight="bold" fill="#1e40af">27.1 KB (-97.0%)</text>

        <!-- Row 4: Event JSON -->
        <text x="147" y="176" text-anchor="end" font-size="12.5" font-weight="bold">Event JSON (/events)</text>
        <rect x="155" y="159" width="5" height="24" fill="#2563eb"/>
        <text x="167" y="176" font-size="12" font-weight="bold" fill="#1e40af">0.18 KB (-99.98%)</text>

        <!-- X axis labels -->
        <text x="155" y="213" text-anchor="middle" font-size="11" fill="#444">0 KB</text>
        <text x="255" y="213" text-anchor="middle" font-size="11" fill="#444">300 KB</text>
        <text x="355" y="213" text-anchor="middle" font-size="11" fill="#444">600 KB</text>
        <text x="455" y="213" text-anchor="middle" font-size="11" fill="#444">900 KB</text>
      </svg>
    </div>

    <div>
      <div class="chart-title">B. Inference &amp; End-to-End Frame Latency (ms)</div>
      <svg width="505" height="235" viewBox="0 0 505 235">
        <line x1="175" y1="15" x2="175" y2="195" stroke="#333" stroke-width="1.2"/>
        <line x1="175" y1="195" x2="485" y2="195" stroke="#333" stroke-width="1.2"/>
        <line x1="255" y1="15" x2="255" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="335" y1="15" x2="335" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="415" y1="15" x2="415" y2="195" stroke="#ccc" stroke-dasharray="3,3"/>

        <!-- Row 1 -->
        <text x="167" y="44" text-anchor="end" font-size="12.5" font-weight="bold">Isolated ONNX (640px)</text>
        <rect x="175" y="27" width="22" height="24" fill="#2563eb"/>
        <text x="204" y="44" font-size="12" font-weight="bold" fill="#1e40af">27.6 ms (~36 FPS)</text>

        <!-- Row 2 -->
        <text x="167" y="88" text-anchor="end" font-size="12.5" font-weight="bold">Isolated E2E (640px)</text>
        <rect x="175" y="71" width="44" height="24" fill="#2563eb"/>
        <text x="226" y="88" font-size="12" font-weight="bold" fill="#1e40af">58.8 ms (50.5–67.0)</text>

        <!-- Row 3 -->
        <text x="167" y="132" text-anchor="end" font-size="12.5" font-weight="bold">Live-Run ONNX (960px)</text>
        <rect x="175" y="115" width="62" height="24" fill="#c4c4b8" stroke="#777" stroke-width="0.8"/>
        <text x="244" y="132" font-size="12" font-weight="bold">85.4 ms (6.6 FPS)</text>

        <!-- Row 4 -->
        <text x="167" y="176" text-anchor="end" font-size="12.5" font-weight="bold">Live-Run E2E (Queue 7/8)</text>
        <rect x="175" y="159" width="248" height="24" fill="#c4c4b8" stroke="#777" stroke-width="0.8"/>
        <text x="429" y="176" font-size="12" font-weight="bold">720.0 ms</text>

        <text x="175" y="213" text-anchor="middle" font-size="11" fill="#444">0 ms</text>
        <text x="255" y="213" text-anchor="middle" font-size="11" fill="#444">250 ms</text>
        <text x="335" y="213" text-anchor="middle" font-size="11" fill="#444">500 ms</text>
        <text x="415" y="213" text-anchor="middle" font-size="11" fill="#444">750 ms</text>
      </svg>
    </div>
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 6: Scientific Column & Bar Charts for SQLite Counts & Frame Retention
# ---------------------------------------------------------------------------
FIG6_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 26px; }}
.chart-title {{ font-size: 14px; font-weight: bold; margin-bottom: 10px; text-align: center; }}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Analytics Console telemetry counters after 4 min 57 s uptime (2,605 debounced events in SQLite)</span>
    <span>Captured 17 Nov 2026 at 10:46:23 during live driveway stream</span>
  </div>
  <div class="two-col">
    <div>
      <div class="chart-title">A. Cumulative Legacy Rule Triggers in SQLite</div>
      <svg width="505" height="225" viewBox="0 0 505 225">
        <!-- Y axis and X axis -->
        <line x1="60" y1="20" x2="60" y2="180" stroke="#333" stroke-width="1.2"/>
        <line x1="60" y1="180" x2="470" y2="180" stroke="#333" stroke-width="1.2"/>
        <!-- Horizontal grid lines -->
        <line x1="60" y1="140" x2="470" y2="140" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="60" y1="100" x2="470" y2="100" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="60" y1="60" x2="470" y2="60" stroke="#ccc" stroke-dasharray="3,3"/>
        <text x="52" y="184" text-anchor="end" font-size="11">0</text>
        <text x="52" y="144" text-anchor="end" font-size="11">50</text>
        <text x="52" y="104" text-anchor="end" font-size="11">100</text>
        <text x="52" y="64" text-anchor="end" font-size="11">150</text>

        <!-- Bar 1: Occupancy spike (74) -> height = 74 * 0.8 = 59.2 -->
        <rect x="105" y="121" width="65" height="59" fill="#c4c4b8" stroke="#666" stroke-width="0.8"/>
        <text x="137" y="114" text-anchor="middle" font-size="12.5" font-weight="bold">74</text>
        <text x="137" y="198" text-anchor="middle" font-size="12">Occupancy spike</text>
        <text x="137" y="212" text-anchor="middle" font-size="10.5" fill="#555">(R1 &middot; &gt;3 persons)</text>

        <!-- Bar 2: Unexpected object (153) -> height = 153 * 0.8 = 122.4 -->
        <rect x="235" y="58" width="65" height="122" fill="#2563eb"/>
        <text x="267" y="51" text-anchor="middle" font-size="12.5" font-weight="bold" fill="#1e40af">153</text>
        <text x="267" y="198" text-anchor="middle" font-size="12">Unexpected object</text>
        <text x="267" y="212" text-anchor="middle" font-size="10.5" fill="#555">(R2 &middot; &ge;5s presence)</text>

        <!-- Bar 3: Object dwell (54) -> height = 54 * 0.8 = 43.2 -->
        <rect x="365" y="137" width="65" height="43" fill="#c4c4b8" stroke="#666" stroke-width="0.8"/>
        <text x="397" y="130" text-anchor="middle" font-size="12.5" font-weight="bold">54</text>
        <text x="397" y="198" text-anchor="middle" font-size="12">Object dwell</text>
        <text x="397" y="212" text-anchor="middle" font-size="10.5" fill="#555">(R3 &middot; &ge;30s unattended)</text>
      </svg>
    </div>

    <div>
      <div class="chart-title">B. Bounded Ingest Queue Accounting (2,859 Frames)</div>
      <svg width="505" height="225" viewBox="0 0 505 225">
        <line x1="150" y1="25" x2="150" y2="175" stroke="#333" stroke-width="1.2"/>
        <line x1="150" y1="175" x2="480" y2="175" stroke="#333" stroke-width="1.2"/>
        <line x1="250" y1="25" x2="250" y2="175" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="350" y1="25" x2="350" y2="175" stroke="#ccc" stroke-dasharray="3,3"/>
        <line x1="450" y1="25" x2="450" y2="175" stroke="#ccc" stroke-dasharray="3,3"/>

        <text x="142" y="58" text-anchor="end" font-size="12.5" font-weight="bold">Frames Received</text>
        <rect x="150" y="40" width="260" height="26" fill="#c4c4b8" stroke="#666" stroke-width="0.8"/>
        <text x="416" y="58" font-size="12" font-weight="bold">2,859 (100%)</text>

        <text x="142" y="106" text-anchor="end" font-size="12.5" font-weight="bold">Frames Processed</text>
        <rect x="150" y="88" width="250" height="26" fill="#2563eb"/>
        <text x="406" y="106" font-size="12" font-weight="bold" fill="#1e40af">2,757 (96.4%)</text>

        <text x="142" y="154" text-anchor="end" font-size="12.5" font-weight="bold">Dropped (Queue Full)</text>
        <rect x="150" y="136" width="12" height="26" fill="#be123c"/>
        <text x="170" y="154" font-size="12" font-weight="bold" fill="#991b1b">102 (3.6% drop-oldest)</text>

        <text x="150" y="196" text-anchor="middle" font-size="11" fill="#444">0</text>
        <text x="250" y="196" text-anchor="middle" font-size="11" fill="#444">1,000</text>
        <text x="350" y="196" text-anchor="middle" font-size="11" fill="#444">2,000</text>
        <text x="450" y="196" text-anchor="middle" font-size="11" fill="#444">3,000</text>
      </svg>
    </div>
  </div>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 7: Scientific Time-Series Plot of the 12 Live Alerts (matching Figs 3 & 4 of previous report)
# ---------------------------------------------------------------------------
FIG7_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Timing, zone and severity progression of the 12 live Telegram alerts (10:44:21 to 10:44:39)</span>
    <span>Blue circle = Warning (7) &middot; Red square = Critical after S5 escalation or interior rule (5)</span>
  </div>
  <svg width="1065" height="285" viewBox="0 0 1065 285">
    <!-- Axes -->
    <line x1="170" y1="20" x2="170" y2="230" stroke="#222" stroke-width="1.3"/>
    <line x1="170" y1="230" x2="1030" y2="230" stroke="#222" stroke-width="1.3"/>

    <!-- Horizontal Swimlanes by Rule Family -->
    <line x1="170" y1="55" x2="1030" y2="55" stroke="#ddd" stroke-dasharray="3,3"/>
    <line x1="170" y1="98" x2="1030" y2="98" stroke="#ddd" stroke-dasharray="3,3"/>
    <line x1="170" y1="141" x2="1030" y2="141" stroke="#ddd" stroke-dasharray="3,3"/>
    <line x1="170" y1="184" x2="1030" y2="184" stroke="#ddd" stroke-dasharray="3,3"/>

    <text x="160" y="59" text-anchor="end" font-size="12.5" font-weight="bold">Person In Zone (H1)</text>
    <text x="160" y="102" text-anchor="end" font-size="12.5" font-weight="bold">Repeat Visit Casing (H15)</text>
    <text x="160" y="145" text-anchor="end" font-size="12.5" font-weight="bold">Fence Approach (H14)</text>
    <text x="160" y="188" text-anchor="end" font-size="12.5" font-weight="bold">Night Person (H2) / Tamper</text>

    <!-- X-axis ticks: t=0 is 10:44:20, scale = 40px per second (t=0..20 -> x=190..990) -->
    <line x1="190" y1="230" x2="190" y2="236" stroke="#222"/>
    <text x="190" y="250" text-anchor="middle" font-size="11.5">10:44:20 (+0s)</text>

    <line x1="390" y1="20" x2="390" y2="230" stroke="#eee"/>
    <line x1="390" y1="230" x2="390" y2="236" stroke="#222"/>
    <text x="390" y="250" text-anchor="middle" font-size="11.5">10:44:25 (+5s)</text>

    <line x1="590" y1="20" x2="590" y2="230" stroke="#eee"/>
    <line x1="590" y1="230" x2="590" y2="236" stroke="#222"/>
    <text x="590" y="250" text-anchor="middle" font-size="11.5">10:44:30 (+10s)</text>

    <line x1="790" y1="20" x2="790" y2="230" stroke="#eee"/>
    <line x1="790" y1="230" x2="790" y2="236" stroke="#222"/>
    <text x="790" y="250" text-anchor="middle" font-size="11.5">10:44:35 (+15s)</text>

    <line x1="990" y1="20" x2="990" y2="230" stroke="#eee"/>
    <line x1="990" y1="230" x2="990" y2="236" stroke="#222"/>
    <text x="990" y="250" text-anchor="middle" font-size="11.5">10:44:40 (+20s)</text>

    <text x="600" y="274" text-anchor="middle" font-size="12.5" font-weight="bold"> Live Run Timeline (Seconds Elapsed Since 10:44:20)</text>

    <!-- Callout line 1: Fail-open at t=+3s (x=310) -->
    <line x1="310" y1="30" x2="310" y2="230" stroke="#666" stroke-width="1" stroke-dasharray="4,4"/>
    <text x="316" y="42" font-size="11.5" font-weight="bold" fill="#333">10:44:23 fail-open recovery</text>
    <text x="316" y="56" font-size="10.5" fill="#555">(OpenAITimeoutError &rarr; still alerts)</text>

    <!-- Callout line 2: S5 Escalation onset at t=+13s (x=710) -->
    <line x1="710" y1="20" x2="710" y2="230" stroke="#be123c" stroke-width="1" stroke-dasharray="4,4"/>
    <text x="702" y="30" text-anchor="end" font-size="11.5" font-weight="bold" fill="#be123c">S5 Repeat Escalation Onset (10:44:33)</text>

    <!-- Data points -->
    <!-- #1: t=1s (x=230), Tamper Moved (Warning) -->
    <circle cx="230" cy="184" r="6" fill="#2563eb"/>
    <text x="230" y="204" text-anchor="middle" font-size="10.5">#1 Tamper (0.98)</text>

    <!-- #2: t=3s (x=310), Night Person (Warning, fail-open) -->
    <circle cx="310" cy="184" r="6" fill="#2563eb"/>
    <text x="310" y="172" text-anchor="middle" font-size="10.5">#2 Night (fail-open)</text>

    <!-- #3: t=11s (x=630), Fence (Warning) -->
    <circle cx="630" cy="141" r="6" fill="#2563eb"/>
    <text x="615" y="131" text-anchor="end" font-size="10.5">#3 fence_line</text>

    <!-- #4 & #5: t=12s (x=670), Casing fence_line & window (Warning) -->
    <circle cx="665" cy="98" r="6" fill="#2563eb"/>
    <circle cx="678" cy="98" r="6" fill="#2563eb"/>
    <text x="665" y="85" text-anchor="middle" font-size="10.5">#4–#5 Casing (fence, window)</text>

    <!-- #6: t=13s (x=710), Night Person (Critical) -->
    <rect x="704" y="178" width="12" height="12" fill="#be123c"/>
    <text x="710" y="204" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#be123c">#6 Night (Critical)</text>

    <!-- #7: t=13s (x=710), Fence (Warning) -->
    <circle cx="710" cy="141" r="6" fill="#2563eb"/>

    <!-- #8 & #10: t=14s (x=750), Person In Zone window (Critical + Warning) -->
    <rect x="742" y="49" width="12" height="12" fill="#be123c"/>
    <circle cx="758" cy="55" r="6" fill="#2563eb"/>
    <text x="768" y="59" text-anchor="start" font-size="10.5">#8 (Crit) &amp; #10 (Warn) window</text>

    <!-- #9: t=14s (x=750), Fence (Critical escalated) -->
    <rect x="744" y="135" width="12" height="12" fill="#be123c"/>
    <text x="764" y="145" font-size="10.5" font-weight="bold" fill="#be123c">#9 Fence (3rd &rarr; Crit)</text>

    <!-- #11: t=17s (x=870), Casing yard (Critical) -->
    <rect x="864" y="92" width="12" height="12" fill="#be123c"/>
    <text x="870" y="84" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#be123c">#11 yard (Crit)</text>

    <!-- #12: t=19s (x=950), Person In Zone door (Critical) -->
    <rect x="944" y="49" width="12" height="12" fill="#be123c"/>
    <text x="950" y="42" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#be123c">#12 door (Crit)</text>
  </svg>
</div></body></html>
"""

# ---------------------------------------------------------------------------
# FIG 8: Clean Webhook Signing & Delivery Sequence Diagram
# ---------------------------------------------------------------------------
FIG8_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMMON_CSS}
.two-col {{ display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 22px; align-items: center; }}
.card-preview {{
  border: 1.2px solid #333;
  background: #f8f8f6;
  padding: 14px 16px;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.55;
}}
</style></head><body><div class="frame">
  <div class="caption-top">
    <span>Signed webhook delivery path (<code>server/alerts.py</code> &rarr; Hermes Gateway <code>:8644</code> &rarr; Telegram Bot API)</span>
    <span>Direct delivery mode (<code>deliver_only: true</code>)</span>
  </div>
  <div class="two-col">
    <svg width="580" height="220" viewBox="0 0 580 220">
      <!-- Actor boxes -->
      <rect x="10" y="10" width="120" height="32" fill="#e8f0fe" stroke="#2563eb" stroke-width="1.5" rx="3"/>
      <text x="70" y="30" text-anchor="middle" font-size="12" font-weight="bold">notify_node</text>

      <rect x="160" y="10" width="125" height="32" fill="#fff" stroke="#444" stroke-width="1.2" rx="3"/>
      <text x="222" y="30" text-anchor="middle" font-size="12" font-weight="bold">alerts.fire()</text>

      <rect x="315" y="10" width="125" height="32" fill="#fff" stroke="#444" stroke-width="1.2" rx="3"/>
      <text x="377" y="30" text-anchor="middle" font-size="12" font-weight="bold">Hermes (:8644)</text>

      <rect x="465" y="10" width="105" height="32" fill="#f4f4f0" stroke="#444" stroke-width="1.2" rx="3"/>
      <text x="517" y="30" text-anchor="middle" font-size="12" font-weight="bold">Telegram API</text>

      <!-- Lifelines -->
      <line x1="70" y1="42" x2="70" y2="205" stroke="#888" stroke-dasharray="4,4"/>
      <line x1="222" y1="42" x2="222" y2="205" stroke="#888" stroke-dasharray="4,4"/>
      <line x1="377" y1="42" x2="377" y2="205" stroke="#888" stroke-dasharray="4,4"/>
      <line x1="517" y1="42" x2="517" y2="205" stroke="#888" stroke-dasharray="4,4"/>

      <!-- Step 1 -->
      <line x1="70" y1="68" x2="218" y2="68" stroke="#222" stroke-width="1.3"/>
      <polygon points="222,68 214,64 214,72" fill="#222"/>
      <text x="146" y="61" text-anchor="middle" font-size="11">1. Confirmed Anomaly + reason</text>

      <!-- Step 2 -->
      <line x1="222" y1="104" x2="373" y2="104" stroke="#2563eb" stroke-width="1.5"/>
      <polygon points="377,104 369,100 369,108" fill="#2563eb"/>
      <text x="300" y="96" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e40af">2. POST /webhooks/house-alert</text>
      <text x="300" y="118" text-anchor="middle" font-size="10" fill="#444">Header: X-Hub-Signature-256 (HMAC-SHA256)</text>

      <!-- Step 3 -->
      <line x1="377" y1="152" x2="513" y2="152" stroke="#222" stroke-width="1.3"/>
      <polygon points="517,152 509,148 509,156" fill="#222"/>
      <text x="447" y="144" text-anchor="middle" font-size="11">3. Verify HMAC &amp; deliver card</text>

      <!-- Step 4 -->
      <line x1="377" y1="188" x2="226" y2="188" stroke="#555" stroke-width="1.1" stroke-dasharray="4,3"/>
      <polygon points="222,188 230,184 230,192" fill="#555"/>
      <text x="300" y="181" text-anchor="middle" font-size="10.5" fill="#444">4. HTTP 200 OK (5.0s non-blocking timeout)</text>
    </svg>

    <div class="card-preview">
      <div style="font-family:'Times New Roman',serif; font-weight:bold; font-size:13px; margin-bottom:6px; border-bottom:1px solid #bbb; padding-bottom:4px;">
        Formatted Card Delivered to Phone
      </div>
      <div><b>CRITICAL &middot; Fence Or Wall Approach</b></div>
      <div style="color:#666;">----------------------</div>
      <div>Camera : edge-01</div>
      <div>Mode &nbsp; : HOME | Zone: fence_line</div>
      <div>Time &nbsp; : 10:44:34</div>
      <div>Event &nbsp;: Person approaching perimeter zone 'fence_line' (2.1s)</div>
      <div>Agent &nbsp;: Person approaching perimeter fence line while armed at night</div>
    </div>
  </div>
</div></body></html>
"""

SPECS = [
    ("fig1_topology", FIG1_HTML, (1200, 700)),
    ("fig2_dataflow", FIG2_HTML, (1200, 550)),
    ("fig3_langgraph", FIG3_HTML, (1200, 550)),
    ("fig4_zones", FIG4_HTML, (1200, 550)),
    ("fig5_payload", FIG5_HTML, (1200, 520)),
    ("fig6_counts", FIG6_HTML, (1200, 520)),
    ("fig7_alert_timeline", FIG7_HTML, (1200, 520)),
    ("fig8_webhook_seq", FIG8_HTML, (1200, 520)),
]


def trim_white(im: Image.Image, pad: int = 8) -> Image.Image:
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if not bbox:
        return im
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(im.width, bbox[2] + pad)
    y1 = min(im.height, bbox[3] + pad)
    return im.crop((x0, y0, x1, y1))


def main():
    for name, html, (w, h) in SPECS:
        html_path = os.path.abspath(os.path.join(FIG_DIR, f"{name}.html"))
        png_path = os.path.abspath(os.path.join(FIG_DIR, f"{name}.png"))
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        file_url = "file:///" + html_path.replace("\\", "/")
        cmd = [
            EDGE_BIN,
            "--headless",
            "--disable-gpu",
            "--force-device-scale-factor=2",
            f"--window-size={w},{h}",
            f"--screenshot={png_path}",
            file_url,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        im = Image.open(png_path).convert("RGB")
        cropped = trim_white(im, pad=8)
        cropped.save(png_path, optimize=True)
        print(f"{name}.png -> {cropped.size[0]}x{cropped.size[1]} ({os.path.getsize(png_path)//1024} KB)")


if __name__ == "__main__":
    main()
