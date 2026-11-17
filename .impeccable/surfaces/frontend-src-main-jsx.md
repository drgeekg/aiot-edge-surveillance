---
version: 1
slug: "frontend-src-main-jsx"
primary_target: "frontend/src/main.jsx"
related_targets: ["frontend/src/AnalyticsApp.jsx","frontend/src/EdgeEmitterApp.jsx","frontend/src/components/ConsoleShell.jsx","frontend/src/styles.css"]
---

# Surface Brief: Edge-to-Server Vision Consoles (:5173 Analytics Console & :5174 Edge Control Deck)

- **Consoles:** Analytics Console (`:5173`, `frontend/src/AnalyticsApp.jsx`), Edge Control Deck (`:5174`, `frontend/src/EdgeEmitterApp.jsx`), shared chrome (`frontend/src/components/ConsoleShell.jsx`), shared stylesheet (`frontend/src/styles.css`).
- **Domain:** Real-time edge-to-server YOLO26n ONNX anomaly and object detection workbench for facility monitoring and live emitter testing.
- **User priority:** Replace the dark brown glassmorphic RoastGlass theme with a genuinely dull, calm matte light theme that reduces eye glare and strips away visual clutter (no floating cards per metric, no emojis, no uppercase kickers, no glass/gradients/shadows, no custom cursor).

## Direction contract
- THESIS: A zero-glare matte ash and unglazed ceramic workspace that strips away dark glass chrome and keeps saturated color strictly quarantined inside the live CV frame, the mineral-teal occupancy line, and active anomaly alerts.
- OWN-WORLD: acoustic studio felt, unglazed matte ceramic, stamped parcel labels; matte warm-grey ash ground (`#E4E5E2`) paired with calm ceramic panel planes (`#F0F0EC`), charcoal ink (`#1F2120`), hairline rules (`#D2D3CE` / `#DFE0DB`), and restrained mineral teal (`#246068`) below 2% of pixels.
- STORY: Chrome stays strictly neutral greyscale without glassmorphism, gradients, drop shadows, serif display fluff, or decorative emojis; all telemetry uses tabular `IBM Plex Sans` + `IBM Plex Mono` (`#555956` secondary text >= 4.5:1 contrast), right-aligned numeric table columns, clean range sliders and labeled source inputs, and persistent muted alert indicators until anomalies clear.
- FIRST VIEWPORT: Quiet 48px flat top bar (console title, single status dot, device/FPS meta, and direct port link to the peer deck), concise `h1` title + 1-line subtitle + freshness stamp, one unified 6-cell hairline-divided metrics strip (`3x2` tablet, `2x3` mobile), underline tab bar with a 2px `#246068` active indicator, and a balanced primary 2-column split pairing the live video monitor on the left with telemetry/source controls on the right.
- FORM: Built from `seed:6144f2a45659ee66` (Overcast Ash & Mineral) across shared tokens (`--ground: #E4E5E2`, `--surface: #F0F0EC`, `--raised: #E9EAE5`, `--border: #D2D3CE`, `--rule: #DFE0DB`, `--text: #1F2120`, `--muted: #555956`, `--accent: #246068`, `--primary: #2B2E2C`), zero shadows/radii clutter (`8px` panel / `6px` control radius), and responsive single-column stacking below 768px with zero horizontal overflow at `390x844`.
- FINISH: Build clean with `npm.cmd run build`, run `impeccable detect --json` and `taste-skill` `lint.mjs --app`, test interactive source switching, encoder updates, and synthetic R1/R2/R3 injection in headless Chromium at `1440x900`, `768x1024`, and `390x844`, inspect every screenshot directly, pass independent finish review, and document the finalized system in `DESIGN.md` and `.impeccable/design.json`.
