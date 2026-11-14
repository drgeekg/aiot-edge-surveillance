# ANOMALY_RULES.md

All rules are evaluated by `RuleEngine` once per processed frame (from the
worker) or once per injected event batch (from `POST /events`), **per
`device_id`**. Per-rule cooldown is 10 s (the same rule cannot re-fire for the
same device within 10 s). Defaults live in `config.yaml`. Rule timing uses the
edge capture timestamp `ts`.

| ID | Rule | Condition (defaults) | Severity | Syllabus mapping |
|---|---|---|---|---|
| R1 | occupancy_spike | `person` count in one frame/batch > `person_threshold: 3` | warning | "occupancy spike" |
| R2 | unexpected_object | class ∈ `watch_classes` [backpack, handbag, suitcase] with a track alive ≥ `unexpected_seconds: 5` | warning | "unexpected object" |
| R3 | object_dwell | watch-list object **unattended** ≥ `dwell_seconds: 30` | critical | "object left too long" |

## R3 definition: "unattended"
- The R3 clock starts when the object's track is first seen, and resets whenever
  a `person` box centre is within `owner_radius: 0.20` (normalized distance) of
  the object's centre.
- The clock also resets if the object moves: IoU between its current box and
  its box ≈ 5 s earlier falls below 0.3.
- Fires when the clock reaches `dwell_seconds`.
- Injected events without person boxes never reset the clock (nobody is "near").
- Injected events without a `box` use a class-wide virtual box
  `(0, 0, 1, 1)`, so dwell means "this class has been continuously present".

## Escalation
A bag left on a chair triggers R2 (warning) at 5 s and R3 (critical) at 30 s,
as long as nobody stands next to it.

## Tracker notes
- Per-device, per-class centroid tracks; a track is destroyed after
  `track_timeout: 3` s without a matching detection.
- R2 and R3 both read the track's lifetime and unattended clock; R1 does not
  use the tracker.
- Every anomaly is inserted into `anomalies` and passed to `alerts.fire()`.

## Why a watch-list (not an allow-list)
An allow-list flags every unlisted COCO class (tv, book, potted plant, cell
phone), so one misdetection raises a warning. Treating any still non-person
object as "abandoned" would fire R3 on chairs and laptops. The watch-list
targets the abandoned-bag scenario from the original Pi brief while covering
crowd (R1), foreign object (R2) and left-behind object (R3).

## config.yaml (rules)
```yaml
rules:
  person_threshold: 3
  watch_classes: [backpack, handbag, suitcase]
  unexpected_seconds: 5
  dwell_seconds: 30
  owner_radius: 0.20
  track_timeout: 3
  cooldown_seconds: 10
```
