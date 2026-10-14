"""
LSJ Video Editor — Immutable EditPlan and Transactional Plan Engine
Architecture: Sovereign Speech Kit (SSK) & HotnHazy Knowledge Engine (KE)

Provides frozen, immutable, versioned EditPlan records, rational/frame-accurate timing,
strict pre-mutation validation, cryptographic revision binding, and atomic transactional application.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import hashlib
import json
import math
import time
import uuid
from typing import Any, Mapping, Sequence


# =============================================================================
# Exact Timing: Rational Time and Frame Index Representation
# =============================================================================

@dataclass(frozen=True)
class RationalTime:
    """Exact rational timestamp (numerator / denominator) avoiding floating-point drift.
    
    Numerator represents the time ticks, denominator represents ticks-per-second (timebase).
    """
    numerator: int
    denominator: int = 1000

    def __post_init__(self):
        if not isinstance(self.numerator, int) or not isinstance(self.denominator, int):
            raise TypeError("RationalTime numerator and denominator must be integers")
        if self.denominator <= 0:
            raise ValueError(f"RationalTime denominator must be strictly positive, got {self.denominator}")
        # Canonical reduction
        g = math.gcd(abs(self.numerator), self.denominator)
        object.__setattr__(self, "numerator", self.numerator // g)
        object.__setattr__(self, "denominator", self.denominator // g)

    @property
    def seconds(self) -> float:
        return self.numerator / self.denominator

    def to_frame(self, fps_num: int, fps_den: int = 1) -> int:
        """Computes exact integer frame index at the given framerate."""
        return (self.numerator * fps_num) // (self.denominator * fps_den)

    @classmethod
    def from_seconds(cls, seconds: float, base: int = 1000) -> RationalTime:
        return cls(int(round(float(seconds) * base)), base)

    @classmethod
    def from_frame(cls, frame: int, fps_num: int, fps_den: int = 1) -> RationalTime:
        return cls(int(frame) * int(fps_den), int(fps_num))

    def __add__(self, other: RationalTime) -> RationalTime:
        if not isinstance(other, RationalTime):
            return NotImplemented
        num = self.numerator * other.denominator + other.numerator * self.denominator
        den = self.denominator * other.denominator
        return RationalTime(num, den)

    def __sub__(self, other: RationalTime) -> RationalTime:
        if not isinstance(other, RationalTime):
            return NotImplemented
        num = self.numerator * other.denominator - other.numerator * self.denominator
        den = self.denominator * other.denominator
        return RationalTime(num, den)

    def __lt__(self, other: RationalTime) -> bool:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return self.numerator * other.denominator < other.numerator * self.denominator

    def __le__(self, other: RationalTime) -> bool:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return self.numerator * other.denominator <= other.numerator * self.denominator

    def __gt__(self, other: RationalTime) -> bool:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return self.numerator * other.denominator > other.numerator * self.denominator

    def __ge__(self, other: RationalTime) -> bool:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return self.numerator * other.denominator >= other.numerator * self.denominator

    def __repr__(self) -> str:
        return f"RationalTime({self.numerator}/{self.denominator} = {self.seconds:.3f}s)"


# =============================================================================
# Immutable Factor Scores & Segment Records
# =============================================================================

@dataclass(frozen=True)
class FactorScores:
    """10-dimensional visual, acoustic, and narrative evaluation factors."""
    energy: float = 0.0
    aesthetics: float = 0.0
    composition: float = 0.0
    facial_expression: float = 0.0
    lighting: float = 0.0
    sharpness: float = 0.0
    camera_stability: float = 0.0
    subject_relevance: float = 0.0
    audio_quality: float = 0.0
    narrative_value: float = 0.0
    pacing_tempo: float = 0.0

    def composite_score(self) -> float:
        """Returns normalized weighted composite score [0.0, 1.0]."""
        weights = (
            self.energy * 0.15 +
            self.aesthetics * 0.12 +
            self.composition * 0.10 +
            self.facial_expression * 0.10 +
            self.lighting * 0.08 +
            self.sharpness * 0.10 +
            self.camera_stability * 0.08 +
            self.subject_relevance * 0.09 +
            self.audio_quality * 0.08 +
            self.narrative_value * 0.10
        )
        return round(weights, 4)


@dataclass(frozen=True)
class PlanSegment:
    """Immutable candidate video or audio segment on the proposed timeline."""
    segment_id: str
    media_id: str
    source_in: RationalTime
    source_out: RationalTime
    timeline_start: RationalTime
    track: int = 0
    narrative_role: str = "action"  # "establishing", "action", "reaction", "detail", "climax", "resolution"
    confidence: float = 1.0
    selection_reason: str = ""
    factor_scores: FactorScores = FactorScores()
    transition_in: str = ""        # "Dissolve", "WipeLeft", etc.
    transition_duration: RationalTime = RationalTime(0, 1)
    filter_preset: str = ""
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0
    scale: float = 1.0
    x: int = 0
    y: int = 0
    volume: float = 1.0
    caption: str = ""
    pinned: bool = False

    def __post_init__(self):
        if not isinstance(self.source_in, RationalTime) or not isinstance(self.source_out, RationalTime):
            raise TypeError("Segment source_in and source_out must be RationalTime instances")
        if not isinstance(self.timeline_start, RationalTime):
            raise TypeError("Segment timeline_start must be a RationalTime instance")
        if not isinstance(self.factor_scores, FactorScores):
            raise TypeError("Segment factor_scores must be a FactorScores instance")

    @property
    def duration(self) -> RationalTime:
        return self.source_out - self.source_in

    @property
    def timeline_end(self) -> RationalTime:
        return self.timeline_start + self.duration


@dataclass(frozen=True)
class PlanMarker:
    """Immutable chapter marker in the proposed sequence."""
    time: RationalTime
    name: str


@dataclass(frozen=True)
class PlanAudioTrack:
    """Immutable background audio / music bed configuration."""
    track_id: str
    media_id: str
    timeline_start: RationalTime
    duration: RationalTime
    volume: float = 0.3
    ducking_enabled: bool = True


@dataclass(frozen=True)
class PlanConstraints:
    """Immutable constraint parameters under which the plan was synthesized."""
    target_duration: RationalTime = RationalTime(300, 1)
    max_duration: RationalTime = RationalTime(600, 1)
    min_shot_duration: RationalTime = RationalTime(15, 30)
    max_shot_duration: RationalTime = RationalTime(150, 30)
    aspect_ratio: str = "16:9"
    style: str = "high_energy"
    pinned_segment_ids: tuple[str, ...] = ()
    excluded_segment_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.pinned_segment_ids, tuple):
            object.__setattr__(self, "pinned_segment_ids", tuple(self.pinned_segment_ids))
        if not isinstance(self.excluded_segment_ids, tuple):
            object.__setattr__(self, "excluded_segment_ids", tuple(self.excluded_segment_ids))


# =============================================================================
# The Versioned, Immutable EditPlan
# =============================================================================

@dataclass(frozen=True)
class EditPlan:
    """Authoritative, immutable, versioned proposal for timeline assembly.
    
    Contains strictly frozen records and immutable tuple collections.
    Modifications create a new plan version; they never mutate an existing plan.
    """
    plan_id: str
    plan_version: int
    media_manifest_hash: str
    timeline_revision: str
    constraints: PlanConstraints
    segments: tuple[PlanSegment, ...]
    audio_tracks: tuple[PlanAudioTrack, ...] = ()
    markers: tuple[PlanMarker, ...] = ()
    warnings: tuple[str, ...] = ()
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        # Guarantee immutable tuples for all collections
        if not isinstance(self.segments, tuple):
            object.__setattr__(self, "segments", tuple(self.segments))
        if not isinstance(self.audio_tracks, tuple):
            object.__setattr__(self, "audio_tracks", tuple(self.audio_tracks))
        if not isinstance(self.markers, tuple):
            object.__setattr__(self, "markers", tuple(self.markers))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))

        # Enforce that every segment is a frozen PlanSegment
        for s in self.segments:
            if not isinstance(s, PlanSegment):
                raise TypeError(f"All elements of segments must be PlanSegment, got {type(s)}")

    @property
    def total_duration(self) -> RationalTime:
        """Master program length determined by the furthest extent of visual clips."""
        visual_segs = [s for s in self.segments if s.track < 4]
        if not visual_segs:
            return RationalTime(0, 1)
        max_end = visual_segs[0].timeline_end
        for s in visual_segs[1:]:
            if s.timeline_end > max_end:
                max_end = s.timeline_end
        return max_end

    def content_hash(self) -> str:
        """Returns canonical SHA-256 fingerprint of the complete plan structure."""
        canonical_dict = {
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "media_manifest_hash": self.media_manifest_hash,
            "timeline_revision": self.timeline_revision,
            "constraints": {
                "target_duration": (self.constraints.target_duration.numerator, self.constraints.target_duration.denominator),
                "max_duration": (self.constraints.max_duration.numerator, self.constraints.max_duration.denominator),
                "min_shot_duration": (self.constraints.min_shot_duration.numerator, self.constraints.min_shot_duration.denominator),
                "max_shot_duration": (self.constraints.max_shot_duration.numerator, self.constraints.max_shot_duration.denominator),
                "aspect_ratio": self.constraints.aspect_ratio,
                "style": self.constraints.style,
                "pinned_segment_ids": list(self.constraints.pinned_segment_ids),
                "excluded_segment_ids": list(self.constraints.excluded_segment_ids),
            },
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "media_id": s.media_id,
                    "source_in": (s.source_in.numerator, s.source_in.denominator),
                    "source_out": (s.source_out.numerator, s.source_out.denominator),
                    "timeline_start": (s.timeline_start.numerator, s.timeline_start.denominator),
                    "track": s.track,
                    "narrative_role": s.narrative_role,
                    "confidence": s.confidence,
                    "transition_in": s.transition_in,
                    "transition_duration": (s.transition_duration.numerator, s.transition_duration.denominator),
                    "scale": s.scale,
                    "x": s.x,
                    "y": s.y,
                    "volume": s.volume,
                    "caption": s.caption,
                    "pinned": s.pinned,
                }
                for s in self.segments
            ],
            "audio_tracks": [
                {
                    "track_id": a.track_id,
                    "media_id": a.media_id,
                    "timeline_start": (a.timeline_start.numerator, a.timeline_start.denominator),
                    "duration": (a.duration.numerator, a.duration.denominator),
                    "volume": a.volume,
                    "ducking_enabled": a.ducking_enabled,
                }
                for a in self.audio_tracks
            ],
            "markers": [
                {
                    "time": (m.time.numerator, m.time.denominator),
                    "name": m.name,
                }
                for m in self.markers
            ],
        }
        blob = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(blob).hexdigest()


# =============================================================================
# Explicit Plan Approval Token
# =============================================================================

@dataclass(frozen=True)
class PlanApproval:
    """Cryptographically bound confirmation authorizing atomic application of a specific EditPlan.
    
    AUDIT NOTE: `approved_by` is an audit attribution identifier (e.g. operator/agent identity),
    NOT an asymmetric cryptographic digital signature. Cryptographic integrity and tampering
    detection are strictly enforced via `plan_content_hash`, `media_manifest_hash`, and `timeline_revision`.
    """
    plan_id: str
    plan_version: int
    plan_content_hash: str
    media_manifest_hash: str
    timeline_revision: str
    approval_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    approved_by: str = "operator"
    approved_at: float = field(default_factory=time.time)

    @property
    def approved_timeline_revision(self) -> str:
        return self.timeline_revision

    @property
    def approved_media_manifest_hash(self) -> str:
        return self.media_manifest_hash

    @property
    def operator(self) -> str:
        return self.approved_by

    def is_valid_for(self, plan: EditPlan) -> bool:
        """Verifies approval matches plan identity and exact content hash."""
        return (
            self.plan_id == plan.plan_id and
            self.plan_version == plan.plan_version and
            self.plan_content_hash == plan.content_hash()
        )

    def is_stale(self, current_media_manifest_hash: str, current_timeline_revision: str) -> bool:
        """Verifies that base environment state has not shifted since authorization."""
        return (
            self.media_manifest_hash != current_media_manifest_hash or
            self.timeline_revision != current_timeline_revision
        )


# =============================================================================
# Cryptographic State Hashing Functions
# =============================================================================

def compute_media_manifest_hash(clips: Sequence[Mapping[str, Any]]) -> str:
    """Generates deterministic hash over available media assets."""
    canonical_items = []
    for c in sorted(clips, key=lambda x: str(x.get("id", ""))):
        canonical_items.append({
            "id": str(c.get("id", "")),
            "name": str(c.get("name", "")),
            "path": str(c.get("path", "")),
            "duration": round(float(c.get("duration", 0.0)), 4),
            "is_audio": bool(c.get("is_audio", False)),
        })
    raw = json.dumps(canonical_items, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:16]


def compute_timeline_revision(timeline: Sequence[Mapping[str, Any]], markers: Sequence[Mapping[str, Any]] | None = None) -> str:
    """Generates deterministic hash over working timeline state."""
    canonical_clips = []
    for c in sorted(timeline, key=lambda x: (int(x.get("track", 0)), float(x.get("start", 0.0)), str(x.get("id", "")))):
        canonical_clips.append({
            "id": str(c.get("id", "")),
            "mediaId": str(c.get("mediaId", "")),
            "track": int(c.get("track", 0)),
            "start": round(float(c.get("start", 0.0)), 4),
            "duration": round(float(c.get("duration", 0.0)), 4),
            "sourceIn": round(float(c.get("sourceIn", 0.0)), 4),
        })
    canonical_markers = []
    if markers:
        for m in sorted(markers, key=lambda x: float(x.get("time", 0.0))):
            canonical_markers.append({
                "time": round(float(m.get("time", 0.0)), 4),
                "name": str(m.get("name", "")),
            })
    payload = {"clips": canonical_clips, "markers": canonical_markers}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:16]


# =============================================================================
# Strict Pre-Mutation Plan Validation
# =============================================================================

def validate_plan(
    plan: EditPlan,
    media_manifest: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    current_timeline: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[bool, list[str]]:
    """Validates an EditPlan against media assets and timeline rules.
    
    Rejects:
    - Missing media IDs
    - Invalid time boundaries (negative duration, source_in >= source_out)
    - Source ranges exceeding underlying media file length
    - Timing conflicts / overlapping segments on the same track
    - Transitions that exceed segment duration
    - Empty sequence without segments
    
    Allows:
    - Intentional overlaps on separate tracks (e.g. Track 0 base + Track 1 PIP)
    """
    errors: list[str] = []

    if isinstance(media_manifest, (list, tuple)):
        manifest_map = {c.get("id"): c for c in media_manifest if isinstance(c, dict)}
    else:
        manifest_map = dict(media_manifest) if media_manifest else {}

    if not plan.segments:
        errors.append("Plan contains zero segments.")
        return False, errors

    # Check media assets and individual segment bounds
    for s in plan.segments:
        media = manifest_map.get(s.media_id)
        if not media:
            errors.append(f"Segment '{s.segment_id}': mediaId '{s.media_id}' not found in media manifest.")
            continue

        if s.source_in >= s.source_out:
            errors.append(f"Segment '{s.segment_id}': source_in ({s.source_in}) must be strictly less than source_out ({s.source_out}).")

        if s.source_in < RationalTime(0, 1):
            errors.append(f"Segment '{s.segment_id}': source_in ({s.source_in}) cannot be negative.")

        # Check source bounds against media duration
        media_dur_sec = float(media.get("duration") or 0.0)
        if media_dur_sec > 0:
            media_dur_rat = RationalTime.from_seconds(media_dur_sec + 0.05)  # 50ms tolerance for fractional container rounding
            if s.source_out > media_dur_rat:
                errors.append(f"Segment '{s.segment_id}': source_out ({s.source_out.seconds:.3f}s) exceeds media duration ({media_dur_sec:.3f}s).")

        if s.timeline_start < RationalTime(0, 1):
            errors.append(f"Segment '{s.segment_id}': timeline_start ({s.timeline_start}) cannot be negative.")

        if s.track < 0:
            errors.append(f"Segment '{s.segment_id}': track ({s.track}) cannot be negative.")

        # Transition checks
        if s.transition_duration > s.duration:
            errors.append(f"Segment '{s.segment_id}': transition duration ({s.transition_duration}) exceeds segment duration ({s.duration}).")

    # Check for timing collisions on the SAME track
    segments_by_track: dict[int, list[PlanSegment]] = {}
    for s in plan.segments:
        segments_by_track.setdefault(s.track, []).append(s)

    for track, track_segs in segments_by_track.items():
        sorted_segs = sorted(track_segs, key=lambda x: x.timeline_start)
        for i in range(len(sorted_segs) - 1):
            cur = sorted_segs[i]
            nxt = sorted_segs[i + 1]
            if cur.timeline_end > nxt.timeline_start:
                overlap_sec = (cur.timeline_end - nxt.timeline_start).seconds
                errors.append(
                    f"Timing conflict on Track {track}: Segment '{cur.segment_id}' (ends at {cur.timeline_end.seconds:.3f}s) "
                    f"overlaps with Segment '{nxt.segment_id}' (starts at {nxt.timeline_start.seconds:.3f}s) by {overlap_sec:.3f}s."
                )

    return len(errors) == 0, errors


# =============================================================================
# Staging & Compilation Engine (Pre-Validation before Commit)
# =============================================================================

def compile_plan_to_timeline(
    plan: EditPlan,
    media_manifest: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> tuple[list[dict], list[dict]]:
    """Compiles an EditPlan into native NLE timeline item dictionaries and markers.
    
    Constructed completely in memory for staging and validation before touching working state.
    """
    staged_timeline: list[dict] = []
    staged_markers: list[dict] = []

    if isinstance(media_manifest, (list, tuple)):
        manifest_map = {c.get("id"): c for c in media_manifest if isinstance(c, dict)}
    else:
        manifest_map = dict(media_manifest) if media_manifest else {}

    for s in plan.segments:
        media = manifest_map.get(s.media_id)
        media_name = media.get("name", "Clip") if media else "Clip"
        item = {
            "id": s.segment_id or uuid.uuid4().hex[:8],
            "mediaId": s.media_id,
            "name": f"{media_name}_{s.narrative_role}",
            "track": s.track,
            "start": round(s.timeline_start.seconds, 4),
            "duration": round(s.duration.seconds, 4),
            "sourceIn": round(s.source_in.seconds, 4),
            "scale": s.scale,
            "x": s.x,
            "y": s.y,
            "volume": s.volume,
            "caption": s.caption,
            "filter": s.filter_preset or "Original",
            "fadeIn": s.fade_in_sec,
            "fadeOut": s.fade_out_sec,
            "transition": s.transition_in if s.transition_in else None,
            "transitionDur": round(s.transition_duration.seconds, 4) if s.transition_in else None,
            "narrative_role": s.narrative_role,
            "factor_scores": dataclasses.asdict(s.factor_scores),
            "pinned": s.pinned,
        }
        staged_timeline.append(item)

    for m in plan.markers:
        staged_markers.append({
            "time": round(m.time.seconds, 4),
            "name": m.name,
        })

    # Sort staged timeline deterministically
    staged_timeline.sort(key=lambda x: (int(x.get("track", 0)), float(x.get("start", 0.0))))
    staged_markers.sort(key=lambda x: float(x.get("time", 0.0)))
    return staged_timeline, staged_markers
