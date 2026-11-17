---
name: "Edge-to-Server Vision Consoles"
description: "Overcast Ash & Mineral matte light design system for Analytics Console (:5173) and Edge Control Deck (:5174)."
colors:
  mineral-teal: "#246068"
  mineral-mist: "#E5ECEC"
  overcast-ash: "#E4E5E2"
  unglazed-ceramic: "#F0F0EC"
  raised-stone: "#E9EAE5"
  pressed-ash: "#E1E2DC"
  warm-chalk: "#F4F4F0"
  pewter-border: "#D2D3CE"
  hairline-rule: "#DFE0DB"
  control-stroke: "#C2C4BE"
  control-stroke-hover: "#AEB1AB"
  charcoal-ink: "#1F2120"
  slate-ash: "#555956"
  graphite-faint: "#616562"
  graphite-primary: "#2B2E2C"
  obsidian-hover: "#1A1C1B"
  stage-charcoal: "#262928"
  stage-silver: "#D7D9D5"
  stage-ash: "#A3A8A3"
  critical-wash: "#F2DFDD"
  critical-ink: "#8B2B24"
  critical-border: "#D9B7B3"
  critical-rule: "#A63A32"
  warning-wash: "#EFE6D5"
  warning-ink: "#7C4F10"
  warning-border: "#D5C19E"
  warning-rule: "#9E6A1C"
  ok-wash: "#DFECE4"
  ok-ink: "#1A4D36"
  ok-border: "#B6CFBF"
  ok-rule: "#2A6E50"
typography:
  headline:
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  metric:
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "21px"
    fontWeight: 500
    lineHeight: 1.2
    fontFeature: "tnum"
  title:
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.45
  body:
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.45
  mono:
    fontFamily: "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
rounded:
  pill: "4px"
  control: "6px"
  panel: "8px"
  full: "50%"
spacing:
  hairline: "1px"
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.graphite-primary}"
    textColor: "{colors.unglazed-ceramic}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.obsidian-hover}"
  button-secondary:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  button-secondary-hover:
    backgroundColor: "{colors.raised-stone}"
  button-danger:
    backgroundColor: "{colors.critical-wash}"
    textColor: "{colors.critical-ink}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  input-text:
    backgroundColor: "{colors.warm-chalk}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "34px"
  panel-card:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.panel}"
    padding: "16px"
  metric-strip:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.panel}"
    padding: "10px 14px"
  tab-navigation:
    backgroundColor: "transparent"
    textColor: "{colors.slate-ash}"
    padding: "8px 2px 9px"
  tab-navigation-active:
    textColor: "{colors.charcoal-ink}"
  status-pill:
    backgroundColor: "{colors.pressed-ash}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  notice-banner:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  source-tile:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    padding: "9px 12px"
  source-tile-active:
    backgroundColor: "{colors.mineral-mist}"
  topbar-link:
    backgroundColor: "{colors.unglazed-ceramic}"
    textColor: "{colors.charcoal-ink}"
    rounded: "{rounded.control}"
    padding: "6px 12px"
---

# Design System: Edge-to-Server Vision Consoles

## Overview

**Creative North Star: "Overcast Ash & Mineral"**

The Overcast Ash & Mineral system serves both decoupled workspaces of the edge-to-server computer-vision pipeline—the **Analytics Console (`:5173`)** and the **Edge Control Deck (`:5174`)**—from one shared matte light stylesheet and component shell. Grounded in the tactile restraint of acoustic studio felt, unglazed matte ceramic, and stamped parcel labels, it keeps sustained monitoring sessions legible and calm on a laptop without eye glare.

Every structural plane stays neutral warm-grey so live operational signals stand out without chrome competition. Saturated color is strictly quarantined inside the 16:9 dark video feed stage, the Mineral Teal occupancy trend line, active navigation markers, and persistent semantic anomaly alerts. Glassmorphism, backdrop blur, drop shadows, surface gradients, uppercase eyebrow kickers, and decorative emojis are excluded across both consoles.

**Key Characteristics:**
- Zero-glare warm neutral canvas (`#E4E5E2`) paired with calm ceramic panel surfaces (`#F0F0EC`) and crisp `1px` hairline rules (`#DFE0DB` / `#D2D3CE`).
- Restrained Mineral Teal (`#246068`) focal accent reserved strictly for active navigation, telemetry traces, focus rings, sliders, and live status dots.
- Quarantined Charcoal Video Stage (`#262928`) isolating raw and YOLO26n-annotated JPEG feeds from light workspace chrome.
- Tabular `IBM Plex Sans` and `IBM Plex Mono` typography delivering jitter-free real-time FPS, latency, count, and timestamp readouts.
- Flat, shadowless plane hierarchy with clean single-column mobile collapse down to `390px` viewports.

## Colors

The palette anchors neutral daylight ergonomics across matte grey-warm ceramic surfaces while isolating Mineral Teal and muted Earth-tone status washes for genuine pipeline signals.

### Primary
- **Mineral Teal** (`#246068`): Single chromatic brand accent used for the active tab underline, occupancy SVG line, range slider thumb, keyboard focus outline, text caret, active video source label, and live status dot.
- **Mineral Mist** (`#E5ECEC`): Quiet desaturated wash applied exclusively to the currently active cell in the Edge Control Deck video source selector matrix.

### Neutral
- **Overcast Ash** (`#E4E5E2`): Global canvas ground and scrollbar track, eliminating bright white screen glare.
- **Unglazed Ceramic** (`#F0F0EC`): Primary surface plane for panels, metric strip cells, secondary buttons, top-bar peer links, range thumb borders, and primary button label ink.
- **Raised Stone** (`#E9EAE5`): Subtle stepped fill for button and table-row hover states, data table headers, and payload code summaries.
- **Pressed Ash** (`#E1E2DC`): Muted fill for disabled buttons, neutral status pills, and non-alert tab count badges.
- **Warm Chalk** (`#F4F4F0`): Recessed-light background for text input fields so editable fields read distinctly against ceramic panels.
- **Pewter Border** (`#D2D3CE`): Outer structural strokes on panels, notice bars, metric strip frame, top-bar divider, tab-bar divider, table header bottom rule, and chart zero axis.
- **Hairline Rule** (`#DFE0DB`): Internal 1px dividers inside lists, key-value rows, table rows, video captions, chart gridlines, and 1px grid gaps inside strips and source matrices.
- **Control Stroke** (`#C2C4BE`): Interactive border stroke on buttons, top-bar peer links, text inputs, range tracks, video stage frames, and scrollbar thumbs.
- **Control Stroke Hover** (`#AEB1AB`): Hover-state border deepening for interactive controls and scrollbar thumbs.
- **Charcoal Ink** (`#1F2120`): High-legibility primary ink for page titles, metric figures, panel headings, and body copy.
- **Slate Ash** (`#555956`): Secondary ink for subtitles, metric labels, timestamps, metadata, table column headers, and disabled button text.
- **Graphite Faint** (`#616562`): Micro-label ink for SVG chart axis ticks, slider scale markers, and idle status dots.
- **Graphite Primary** (`#2B2E2C`): High-contrast dark neutral fill for primary action buttons (`Switch`, `Save Settings`, `Resume Stream`).
- **Obsidian Hover** (`#1A1C1B`): Hover fill darkening for primary action buttons.
- **Stage Charcoal** (`#262928`): Quarantined dark matte backdrop for the 16:9 live raw and annotated video feed containers.
- **Stage Silver** (`#D7D9D5`): Empty-state primary text inside the dark video feed stage.
- **Stage Ash** (`#A3A8A3`): Empty-state instructional subtext inside the dark video feed stage.

### Semantic Status
- **Critical Wash / Ink / Border / Rule** (`#F2DFDD` / `#8B2B24` / `#D9B7B3` / `#A63A32`): Muted terracotta alert palette for active R1/R2/R3 anomaly notices, critical severity pills, alert tab badges, danger trigger buttons, critical status dots, and the dashed chart threshold line (`Limit > 3`).
- **Warning Wash / Ink / Border / Rule** (`#EFE6D5` / `#7C4F10` / `#D5C19E` / `#9E6A1C`): Muted ochre alert palette for backend/controller stalled notices, paused emitter status, warning severity pills, and warning status dots.
- **OK Wash / Ink / Border / Rule** (`#DFECE4` / `#1A4D36` / `#B6CFBF` / `#2A6E50`): Muted sage confirmation palette for transient configuration-saved banners, healthy status pills, and ok status dots.

### Named Rules
**The Mineral Quarantine Rule.** Saturated color is restricted to the live computer-vision video frame, the Mineral Teal (`#246068`) telemetry polyline and active navigation markers, and semantic anomaly/status badges; workspace chrome remains strictly matte neutral.

**The Ink-Contrast Floor Rule.** Every foreground-on-surface pairing meets or exceeds WCAG AA 4.5:1 contrast, ranging from Charcoal Ink on Ceramic (`14.18:1`) down to Slate Ash on Overcast Ash (`5.63:1`) and Graphite Faint on Overcast Ash (`4.68:1`).

## Typography

**Display Font:** None (operational consoles omit an editorial display tier; headings top out at `24px`).
**Body Font:** `IBM Plex Sans` (fallback `system-ui, -apple-system, 'Segoe UI', sans-serif`)
**Label/Mono Font:** `IBM Plex Mono` (fallback `ui-monospace, SFMono-Regular, Menlo, monospace`)

**Character:** Direct, low-fatigue Swiss technical clarity combining humanist grotesque headings and labels with crisp monospace machine telemetry. Every numerical counter, timestamp, and axis readout uses tabular alignment so live polling ticks never shift layout horizontally.

### Hierarchy
- **Headline** (`600`, `24px`, `1.25` line-height, `-0.015em` tracking): Page-level console title (`Live Pipeline Monitor`, `Edge Emitter Control`) paired with a single-line `13px` subtitle and right-aligned `12.5px` freshness stamp.
- **Metric** (`500`, `21px` desktop / `19px` mobile `<=560px`, `1.2` line-height, tabular numerals): Primary values inside the 6-cell telemetry strip, paired with inline `12px` unit suffixes.
- **Title** (`600`, `15px`, `1.45` line-height): Top-bar brand wordmark (`-0.01em` tracking) and panel card headings.
- **Body** (`400` / `500` active, `14px`, `1.45` line-height): Base document scale and top-level tab navigation items (`12.5px` on mobile `<=560px`).
- **Control & Table Copy** (`400` / `500`, `13px`, `1.45` line-height): Buttons, text inputs, notice banners, form labels, key-value keys, card descriptions, subtitles, and table cells (`13.5px` weight `500` on video source titles).
- **Label** (`400` / `500`, `12px`, `1.45` line-height): Metric strip labels, panel metadata (`12px`), table column headers, status pills, small buttons, form hints, and compact timestamps (`12.5px` for top-bar metadata and freshness stamps).
- **Mono** (`400`, `12px` tables/badges / `12.5px` key-value readouts & monospace inputs, `1.45` line-height, tabular numerals): Timestamps, device IDs, rule identifiers, source paths, URLs, and numeric table columns.
- **Micro-Labels** (`400` / `500`, `10.5px`–`11.5px`): Payload summary blocks (`11.5px` monospace), SVG chart threshold labels and range scale ticks (`11px`), tab count badges (`11px` desktop / `10.5px` mobile), and SVG chart axis ticks (`10.5px` monospace).

### Named Rules
**The Tabular Telemetry Rule.** All live KPI cells, timestamps, table columns, axis ticks, and slider readouts enforce `font-variant-numeric: tabular-nums` so streaming updates never jitter alignment.

**The Earned Monospace Rule.** `IBM Plex Mono` is applied exclusively to machine identifiers, timestamps, paths, payload previews, and numeric data columns rather than decorative prose styling.

## Layout

Both consoles share a centered `1220px` single-shell container (`10px` top, `24px` horizontal, `32px` bottom padding on desktop; `16px` horizontal, `28px` bottom padding at `<=768px`) that stacks vertically through five predictable bands: a compact flat top bar (`min-height: 46px`, `8px` bottom padding, `12px` bottom margin), a quiet page header (`14px` bottom margin), conditional full-width notice banners (`14px` bottom margin), a unified 6-cell telemetry strip (`12px` bottom margin), and an underline tab bar (`14px` bottom margin) switching the active workspace grid.

Primary grids organize operational workflows without nesting cards: Analytics Live Monitor uses an asymmetric `1.42fr / 1fr` two-column split pairing the video stage on the left with a stacked `16px`-gap column of timeline chart and recent anomalies on the right; Nodes & Rules and Edge Control Deck Views (`Video Source`, `Encoder`) use equal `2`-column grids; and Edge Event Injector uses an equal-stretch `3`-column grid. Below `1024px`, the metric strip reflows from `6` columns to `3x2` and the injector grid collapses to `2` columns; below `900px`, two-column splits collapse to `1` column; below `768px`, the injector grid collapses to `1` column; below `640px`, the source selector matrix collapses from `2` columns to `1`; and below `560px`, the metric strip compacts to `2x3` (`19px` values), input rows and form labels stack vertically, and non-alert tab count badges hide so tabs fit cleanly without wrapping.

### Named Rules
**The Single-Strip Telemetry Rule.** Top-line pipeline and emitter KPIs live inside one unified 6-cell hairline-divided strip rather than six separate floating cards.

**The Zero-Overflow Rule.** Root horizontal overflow is suppressed (`overflow-x: hidden`), wide tables scroll horizontally inside an isolated table wrapper, and grids step cleanly down to `390px` mobile width without clipped controls.

## Elevation & Depth

This system uses **no shadows**. Zero `box-shadow`, elevation glow, or `backdrop-filter` rules exist anywhere in the stylesheet.

Depth and containment rely exclusively on flat tonal stepping (`#E4E5E2` ground -> `#E9EAE5` raised headers/hover fills -> `#F0F0EC` ceramic panels -> `#F4F4F0` recessed-light inputs) bounded by crisp `1px` solid strokes (`#D2D3CE` structural borders, `#DFE0DB` internal dividers, `#C2C4BE` interactive control outlines).

### Named Rules
**The Zero-Shadow Plane Rule.** Surfaces stay completely flat with zero drop shadows, blur halos, or gradients at rest or on hover; hierarchy is conveyed solely by tonal plane contrast and `1px` rules.

## Shapes

Corners stay restrained and utilitarian across both consoles: `8px` (`--radius-panel`) on major surface panels and the outer unified metric strip frame; `6px` (`--radius-control`) on buttons, top-bar peer links, text inputs, notice banners, code summary boxes, the quarantined video stage, and the source selector matrix frame; `4px` (`--radius-pill`) on severity pills, tab badges, and scrollbar thumbs; `50%` circles on status dots (`8px`) and range slider thumbs (`14px`); and `2px` rounding on `4px`-tall range slider tracks.

### Named Rules
**The Hairline Matrix Rule.** Multi-cell containers (the 6-cell telemetry strip and the 2-column video source selector matrix) render crisp `1px` internal dividers by laying out cells with a `1px` grid gap over a `--rule` (`#DFE0DB`) background inside a clipped `--border` (`#D2D3CE`) outer frame.

## Components

Every component is built from unglazed ceramic planes, crisp `1px` strokes, and `80ms`–`120ms` color/border micro-transitions without decorative ornament.

### Buttons
Compact `34px`-tall tactile controls (`28px` for inline small buttons) with zero shadow and `120ms ease` background/border transitions.
- **Shape:** Gently rounded control corners (`6px` radius), `1px` solid border, `0 12px` horizontal padding (`0 10px` on small `28px` buttons), `13px` medium (`500`) text (`12px` on small buttons).
- **Primary:** Graphite Primary (`#2B2E2C`) fill and border with Unglazed Ceramic (`#F0F0EC`) text, darkening to Obsidian Hover (`#1A1C1B`) on hover.
- **Hover / Focus:** Secondary buttons shift from Unglazed Ceramic (`#F0F0EC`) to Raised Stone (`#E9EAE5`) and deepen border from `#C2C4BE` to `#AEB1AB`; all buttons show a `2px` solid Mineral Teal (`#246068`) `:focus-visible` outline with `2px` offset.
- **Secondary / Danger / Disabled:** Secondary uses `#F0F0EC` fill with `#1F2120` text and `#C2C4BE` border; Danger uses Critical Wash (`#F2DFDD`), Critical Ink (`#8B2B24`), and Critical Border (`#D9B7B3`); Disabled flattens to Pressed Ash (`#E1E2DC`) with Slate Ash (`#555956`) text. Full-width action buttons span `100%` inside injector cards.

### Chips
Quiet, borderless inline status indicators and count badges that separate signal severity without pill clutter.
- **Style:** `4px` pill radius, `2px 8px` padding (`1px 6px` on tab badges), `12px` medium (`500`) text (`11px` on tab badges, `10.5px` on mobile), neutral Pressed Ash (`#E1E2DC`) base fill.
- **State:** Critical (`#F2DFDD` / `#8B2B24`), Warning (`#EFE6D5` / `#7C4F10`), and OK/Info (`#DFECE4` / `#1A4D36`) tint shifts; tab alert badges switch to Critical Wash/Ink and stay visible at mobile `<=560px` while neutral count badges hide.

### Cards / Containers
Flat ceramic planes bounded by `1px` Pewter Borders, avoiding nested cards or shadow elevation.
- **Corner Style:** `8px` radius on panels and the unified metric strip; `6px` radius on notice banners.
- **Background:** Unglazed Ceramic (`#F0F0EC`), shifting to semantic Critical/Warning/OK wash fills on alert and status notice bars.
- **Shadow Strategy:** Zero shadows (per The Zero-Shadow Plane Rule).
- **Border:** `1px` solid `#D2D3CE` (matching semantic border tints on active notice banners).
- **Internal Padding:** `16px` on standard panels (`14px 16px` header + `12px 16px 16px` body on flush table panels), `10px 14px` on metric cells and notice banners.

### Inputs / Fields
Clean, high-legibility operational form controls themed across text inputs, sliders, carets, and selections.
- **Style:** Text inputs use `34px` height, `0 10px` padding, Warm Chalk (`#F4F4F0`) fill, `1px` Control Stroke (`#C2C4BE`), and `6px` radius (with `12.5px` `IBM Plex Mono` for URLs/device IDs). Range sliders use a `4px`-tall Control Stroke track (`2px` radius) and a `14px` circular Mineral Teal (`#246068`) thumb ringed by a `2px` Unglazed Ceramic (`#F0F0EC`) border.
- **Focus:** `2px` solid Mineral Teal (`#246068`) outline with `2px` offset (`:focus-visible`), paired with a Mineral Teal text caret (`caret-color`) and muted teal-ash text selection.
- **Layout:** Label and hint/value readout sit on one flex header line above `6px`-spaced controls and collapse vertically below `560px`.

### Navigation
Dual-tier chrome combining a cross-port top bar with underline workspace tabs.
- **Top Navigation Bar:** `46px` minimum height (`8px` bottom padding, `12px` bottom margin) over a `1px` `#D2D3CE` divider; pairs an `8px` status dot, `15px` semibold title, and `12px` tabular port tag on the left with `12.5px` telemetry metadata and a bordered ceramic peer-deck link (`6px 12px` padding, `6px` radius, `13px` inline diagonal arrow SVG) on the right.
- **Underline Tab Bar:** Horizontal flex strip (`22px` gap desktop, `11px` mobile) over a `1px` `#D2D3CE` divider; inactive tabs render in `14px` weight `400` Slate Ash (`#555956`), transition in `80ms ease` to Charcoal Ink (`#1F2120`) on hover, and lock to weight `500` Charcoal Ink with a `2px` solid Mineral Teal (`#246068`) bottom rule when active.

### Signature Components
- **Quarantined Video Stage:** `16:9` aspect-ratio container (`min-height: 240px`) on Stage Charcoal (`#262928`) with a `1px` `#C2C4BE` stroke and `6px` radius, displaying contained live JPEG frames (`object-fit: contain`) or centered Stage Silver/Ash waiting guidance above a `1px` rule-separated telemetry caption row.
- **Occupancy Timeline Chart:** Responsive inline SVG plot (`460x148` viewBox) drawing horizontal `#DFE0DB` / `#D2D3CE` gridlines, `10.5px` monospace `#616562` ticks, a `1px` dashed `#A63A32` threshold line (`Limit > 3`), and a `2px` rounded Mineral Teal (`#246068`) polyline.
- **Source Selector Matrix:** `2`-column hairline-divided grid (`1`-column `<=640px`) inside a `6px` `#D2D3CE` border; idle tiles sit on Unglazed Ceramic (`#F0F0EC`), hover to Raised Stone (`#E9EAE5`), and highlight the active stream in Mineral Mist (`#E5ECEC`) with a Mineral Teal (`#246068`) `Active` label.
- **Data Tables & Key-Value Lists:** Flush panels housing horizontally scrollable tabular-numeric tables (`12px` Slate Ash headers on `#E9EAE5`, `10px 14px` body cells, right-aligned numeric columns, `#E9EAE5` row hover) and `9px`-padded key-value rows separated by `1px` `#DFE0DB` rules.

## Do's and Don'ts

### Do:
- **Do** keep page ground at Overcast Ash (`#E4E5E2`) and surface panels at Unglazed Ceramic (`#F0F0EC`) separated by `1px` Pewter Border (`#D2D3CE`) and Hairline Rule (`#DFE0DB`) strokes.
- **Do** reserve Mineral Teal (`#246068`) for active tab underlines, SVG occupancy lines, range slider thumbs, focus outlines, text carets, active source status labels, and live status dots.
- **Do** quarantine high-contrast dark tones (`#262928`) exclusively inside the 16:9 video feed stage so live bounding boxes remain legible without glazing surrounding chrome.
- **Do** apply `IBM Plex Mono` (`font-variant-numeric: tabular-nums`) to timestamps, device IDs, rule slugs, telemetry figures, and right-aligned numeric table cells.
- **Do** keep browser surfaces themed from the palette: `2px` Mineral Teal focus outlines with `2px` offset, Mineral Teal caret, custom scrollbars, and `3px` link underline offset.

### Don't:
- **Don't** add drop shadows, backdrop blur, glassmorphism, translucent fills, or surface gradients to panels, controls, or navigation bars.
- **Don't** place uppercase eyebrow kickers above headings, emoji glyphs inside controls or labels, or decorative icons on metric strips and rule cards.
- **Don't** split the 6-cell telemetry strip into six standalone floating cards or exceed `1px` border widths on panels, notices, or list dividers.
- **Don't** apply monospace styling as ornamental flair on descriptive prose headings or marketing labels.
- **Don't** introduce un-tokenized hex colors or duplicate custom properties when extending hover, selection, or semantic states.
