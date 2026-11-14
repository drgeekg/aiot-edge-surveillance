import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Box = Tuple[float, float, float, float]
DEFAULT_BOX: Box = (0.0, 0.0, 1.0, 1.0)


def box_center(b: Box) -> Tuple[float, float]:
    """Return the normalized center coordinates (cx, cy) of bounding box b."""
    return ((b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5)


def box_bottom_center(b: Box) -> Tuple[float, float]:
    """Return the normalized bottom-center foot coordinates (cx, y2) of box b."""
    return ((b[0] + b[2]) * 0.5, b[3])


def center_distance(a: Box, b: Box) -> float:
    """Return Euclidean distance between the centers of normalized boxes a and b."""
    ax, ay = box_center(a)
    bx, by = box_center(b)
    return math.hypot(ax - bx, ay - by)


def box_iou(a: Box, b: Box) -> float:
    """Compute Intersection-over-Union in [0.0, 1.0] for two normalized boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0.0 else 0.0


@dataclass
class Track:
    """Stateful trajectory record for a tracked person or watch-list object."""

    class_name: str
    first_seen: float
    last_seen: float
    box: Box
    anchor_box: Box
    anchor_ts: float
    last_person_near_ts: float
    track_id: int = 0
    owner_id: Optional[int] = None
    last_near_person_id: Optional[int] = None
    hits: int = 1
    history: List[Tuple[float, Box]] = field(default_factory=list)
    near_since: Dict[int, float] = field(default_factory=dict)
    zone_entered_ts: Dict[str, float] = field(default_factory=dict)

    def speed(self, window_s: float = 1.5) -> float:
        """Estimate center movement speed (normalized units/sec) over recent history."""
        recent = [(ht, hb) for ht, hb in self.history if (self.last_seen - ht) <= window_s]
        if len(recent) < 2:
            return 0.0
        t0, b0 = recent[0]
        t1, b1 = recent[-1]
        dt = t1 - t0
        if dt <= 0.05:
            return 0.0
        return center_distance(b0, b1) / dt


class Tracker:
    """Multi-object IoU/centroid tracker with confidence hysteresis and owner binding."""

    def __init__(
        self,
        track_timeout: float = 15.0,
        owner_radius: float = 0.20,
        conf_enter: float = 0.40,
        conf_stay: float = 0.30,
        confirm_frames: int = 1,
    ):
        """Initialize tracking thresholds, occlusion timeouts, and active track tables."""
        self.track_timeout = float(track_timeout)
        self.owner_radius = float(owner_radius)
        self.conf_enter = float(conf_enter)
        self.conf_stay = float(conf_stay)
        self.confirm_frames = max(1, int(confirm_frames))
        self._next_id: int = 1
        self.tracks: Dict[str, List[Track]] = {}
        self.person_tracks: List[Track] = []
        self.recently_pruned: List[Tuple[float, Track]] = []

    def _alloc_id(self) -> int:
        """Allocate and return the next unique sequential track identifier."""
        tid = self._next_id
        self._next_id += 1
        return tid

    def _update_person_tracks(self, person_dets: List[Tuple[Box, float]], ts: float) -> List[Track]:
        """Match and update visible person trajectories for proximity and owner checks."""
        # Person tracks survive up to track_timeout so returning owner retains identity
        self.person_tracks = [
            p for p in self.person_tracks if (ts - p.last_seen) <= self.track_timeout
        ]
        unmatched = list(range(len(self.person_tracks)))
        visible_persons: List[Track] = []

        for b, conf in person_dets:
            if conf < self.conf_stay:
                continue
            best_idx = None
            best_score = None
            for idx in unmatched:
                ptr = self.person_tracks[idx]
                iou = box_iou(ptr.box, b)
                dist = center_distance(ptr.box, b)
                if iou > 0.0 or dist <= 0.25:
                    score = (iou, -dist)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_idx = idx

            if best_idx is not None:
                unmatched.remove(best_idx)
                ptr = self.person_tracks[best_idx]
                ptr.last_seen = ts
                ptr.box = b
                ptr.hits += 1
                ptr.history.append((ts, b))
                ptr.history = [(ht, hb) for ht, hb in ptr.history if ts - ht <= 5.0]
                visible_persons.append(ptr)
            elif conf >= self.conf_enter:
                ptr = Track(
                    class_name="person",
                    first_seen=ts,
                    last_seen=ts,
                    box=b,
                    anchor_box=b,
                    anchor_ts=ts,
                    last_person_near_ts=ts,
                    track_id=self._alloc_id(),
                    hits=1,
                    history=[(ts, b)],
                )
                self.person_tracks.append(ptr)
                visible_persons.append(ptr)

        return visible_persons

    @staticmethod
    def _is_person_stationary(ptr: Track, ts: float, window_s: float = 2.0) -> bool:
        """Return True when a person's center stayed within 0.10 units over window_s."""
        recent = [hb for ht, hb in ptr.history if ts - ht <= window_s]
        if not recent:
            return True
        return center_distance(recent[0], ptr.box) <= 0.10

    def update(self, detections: List[dict], ts: float, watch_classes: List[str] | None = None) -> List[Track]:
        """Update person and watch-object tracks for a frame, returning confirmed tracks."""
        # 1. Prune expired tracks across all watch classes (15s lost state)
        self.recently_pruned = [(pt, tr) for pt, tr in self.recently_pruned if (ts - pt) <= 30.0]
        for cls in list(self.tracks.keys()):
            kept: List[Track] = []
            for t in self.tracks[cls]:
                if (ts - t.last_seen) <= self.track_timeout:
                    kept.append(t)
                else:
                    self.recently_pruned.append((ts, t))
            self.tracks[cls] = kept

        # 2. Separate person boxes and watch-class detections with confidence
        person_dets: List[Tuple[Box, float]] = [
            (tuple(d["box"]) if d.get("box") is not None else DEFAULT_BOX, float(d.get("conf", d.get("avg_conf", 1.0))))
            for d in detections
            if d.get("class_name") == "person" and d.get("box") is not None
        ]
        visible_persons = self._update_person_tracks(person_dets, ts)
        person_boxes: List[Box] = [p.box for p in visible_persons]

        by_class: Dict[str, List[Tuple[Box, float]]] = {}
        for d in detections:
            cls = d.get("class_name")
            if not cls or cls == "person":
                continue
            if watch_classes is not None and cls not in watch_classes:
                continue
            conf = float(d.get("conf", d.get("avg_conf", 1.0)))
            if conf < self.conf_stay:
                continue
            box = tuple(d["box"]) if d.get("box") is not None else DEFAULT_BOX
            count = int(d.get("count", 1))
            for _ in range(max(1, count)):
                by_class.setdefault(cls, []).append((box, conf))

        # 3. Greedy match per class by IoU, then centroid distance (with confidence hysteresis)
        for cls, det_items in by_class.items():
            existing = self.tracks.setdefault(cls, [])
            unmatched_tracks = list(range(len(existing)))
            for b, conf in det_items:
                best_idx = None
                best_score = None
                for idx in unmatched_tracks:
                    tr = existing[idx]
                    iou = box_iou(tr.box, b)
                    dist = center_distance(tr.box, b)
                    if iou > 0.0 or dist <= 0.25:
                        score = (iou, -dist)
                        if best_score is None or score > best_score:
                            best_score = score
                            best_idx = idx

                if best_idx is not None:
                    unmatched_tracks.remove(best_idx)
                    tr = existing[best_idx]
                    tr.last_seen = ts
                    tr.box = b
                    tr.hits += 1
                    tr.history.append((ts, b))
                    tr.history = [(ht, hb) for ht, hb in tr.history if ts - ht <= 10.0]
                    # Anchor box: position approximately 5 s ago
                    older = [hb for ht, hb in tr.history if ts - ht >= 5.0]
                    anchor = older[-1] if older else tr.history[0][1]
                    tr.anchor_box = anchor
                    if box_iou(b, tr.anchor_box) < 0.3:
                        # Reset on displacement ONLY if a person is within owner_radius
                        near_p = [p for p in visible_persons if center_distance(p.box, b) <= self.owner_radius]
                        if near_p:
                            tr.last_person_near_ts = ts
                            tr.last_near_person_id = near_p[0].track_id
                        tr.history = [(ts, b)]
                        tr.anchor_box = b
                elif conf >= self.conf_enter:
                    # Bind nearest visible person within owner_radius at first_seen as owner
                    nearest_owner_id: Optional[int] = None
                    best_p_dist = None
                    for ptr in visible_persons:
                        d_p = center_distance(ptr.box, b)
                        if d_p <= self.owner_radius and (best_p_dist is None or d_p < best_p_dist):
                            best_p_dist = d_p
                            nearest_owner_id = ptr.track_id

                    existing.append(
                        Track(
                            class_name=cls,
                            first_seen=ts,
                            last_seen=ts,
                            box=b,
                            anchor_box=b,
                            anchor_ts=ts,
                            last_person_near_ts=ts,
                            track_id=self._alloc_id(),
                            owner_id=nearest_owner_id,
                            last_near_person_id=nearest_owner_id,
                            hits=1,
                            history=[(ts, b)],
                        )
                    )

        # 4. Check person proximity against all active tracks (owner OR stationary person >= 2s)
        active: List[Track] = []
        for cls_tracks in self.tracks.values():
            for tr in cls_tracks:
                current_near_ids = set()
                should_reset = False
                for ptr in visible_persons:
                    if center_distance(ptr.box, tr.box) <= self.owner_radius:
                        current_near_ids.add(ptr.track_id)
                        tr.last_near_person_id = ptr.track_id
                        start_t = tr.near_since.setdefault(ptr.track_id, ts)
                        if tr.owner_id is not None and ptr.track_id == tr.owner_id:
                            should_reset = True
                        elif (ts - start_t) >= 2.0 and self._is_person_stationary(ptr, ts):
                            should_reset = True
                            if tr.owner_id is None:
                                tr.owner_id = ptr.track_id

                for pid in list(tr.near_since.keys()):
                    if pid not in current_near_ids:
                        del tr.near_since[pid]

                if should_reset:
                    tr.last_person_near_ts = ts
                if tr.hits >= self.confirm_frames:
                    active.append(tr)
        return active
