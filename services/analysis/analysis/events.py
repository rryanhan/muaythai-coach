from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Literal

from analysis.calibration import CalibrationProfile, Stance
from analysis.gating import FrameGate
from analysis.pose import Landmark, PoseFrame
from analysis.quality import distance_2d

EventType = Literal["lead_hand_motion", "rear_hand_motion", "body_movement"]
EventEndReason = Literal["returned", "lost_tracking", "timeout", "clip_end"]


@dataclass(frozen=True)
class MotionEvent:
    # A motion event is still generic: it says "something moved enough to inspect."
    # Strike/movement modules decide what that motion means.
    event_type: EventType
    start_ms: float
    peak_ms: float
    end_ms: float
    duration_ms: float
    peak_value: float
    end_reason: EventEndReason
    available_ratio: float
    frame_count: int
    direction: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventSummary:
    events: list[MotionEvent]
    counts_by_type: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return {
            "events": [event.to_json() for event in self.events],
            "counts_by_type": self.counts_by_type,
        }


@dataclass(frozen=True)
class _HandSample:
    frame_index: int
    timestamp_ms: float
    available: bool
    extension_ratio: float


@dataclass(frozen=True)
class _MovementSample:
    frame_index: int
    timestamp_ms: float
    available: bool
    dx: float
    dy: float
    radius: float


def detect_motion_events(
    frames: list[PoseFrame],
    gates: list[FrameGate],
    calibration_profile: CalibrationProfile,
    stance: Stance,
) -> EventSummary:
    lead_samples = _hand_samples(
        frames=frames,
        gates=gates,
        side=_lead_side(stance),
        use_gate=lambda gate: gate.lead_hand_available,
        guard_distance=calibration_profile.lead_reach.guard_distance,
        travel_distance=calibration_profile.lead_reach.travel_distance,
    )
    rear_samples = _hand_samples(
        frames=frames,
        gates=gates,
        side=_rear_side(stance),
        use_gate=lambda gate: gate.rear_hand_available,
        guard_distance=calibration_profile.rear_reach.guard_distance,
        travel_distance=calibration_profile.rear_reach.travel_distance,
    )
    movement_samples = _movement_samples(frames, gates)

    events = [
        *_detect_hand_motion_events("lead_hand_motion", lead_samples),
        *_detect_hand_motion_events("rear_hand_motion", rear_samples),
        *_detect_body_movement_events(movement_samples, calibration_profile),
    ]
    events = sorted(events, key=lambda event: (event.start_ms, event.event_type))
    counts_by_type: dict[str, int] = {}
    for event in events:
        counts_by_type[event.event_type] = counts_by_type.get(event.event_type, 0) + 1
    return EventSummary(events=events, counts_by_type=counts_by_type)


def _hand_samples(
    *,
    frames: list[PoseFrame],
    gates: list[FrameGate],
    side: str,
    use_gate: Any,
    guard_distance: float | None,
    travel_distance: float | None,
) -> list[_HandSample]:
    samples: list[_HandSample] = []
    for frame, gate in zip(frames, gates, strict=True):
        landmarks = frame.landmark_map()
        shoulder = _visible(landmarks.get(f"{side}_shoulder"))
        wrist = _visible(landmarks.get(f"{side}_wrist"))
        available = bool(use_gate(gate)) and shoulder is not None and wrist is not None
        if (
            available
            and shoulder is not None
            and wrist is not None
            and guard_distance is not None
            and travel_distance
            and travel_distance > 0
        ):
            distance = distance_2d(wrist, shoulder)
            extension_ratio = max(0.0, (distance - guard_distance) / travel_distance)
        else:
            extension_ratio = 0.0
        samples.append(
            _HandSample(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                available=available,
                extension_ratio=round(extension_ratio, 3),
            )
        )
    return samples


def _movement_samples(frames: list[PoseFrame], gates: list[FrameGate]) -> list[_MovementSample]:
    centers = [
        _hip_center(frame) if gate.movement_available else None
        for frame, gate in zip(frames, gates, strict=True)
    ]
    valid_centers = [center for center in centers if center is not None]
    if not valid_centers:
        return [
            _MovementSample(frame.frame_index, frame.timestamp_ms, False, 0.0, 0.0, 0.0)
            for frame in frames
        ]

    initial_window = valid_centers[: max(3, min(15, len(valid_centers)))]
    baseline_x = mean(center[0] for center in initial_window)
    baseline_y = mean(center[1] for center in initial_window)
    samples: list[_MovementSample] = []
    for frame, center in zip(frames, centers, strict=True):
        if center is None:
            samples.append(
                _MovementSample(frame.frame_index, frame.timestamp_ms, False, 0.0, 0.0, 0.0)
            )
            continue
        dx = center[0] - baseline_x
        dy = center[1] - baseline_y
        radius = (dx**2 + dy**2) ** 0.5
        samples.append(
            _MovementSample(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                available=True,
                dx=round(dx, 3),
                dy=round(dy, 3),
                radius=round(radius, 3),
            )
        )
    return samples


def _detect_hand_motion_events(
    event_type: EventType,
    samples: list[_HandSample],
    start_threshold: float = 0.35,
    return_threshold: float = 0.22,
    min_peak: float = 0.55,
    min_duration_ms: float = 80.0,
    max_duration_ms: float = 1800.0,
    max_tracking_gap_ms: float = 180.0,
) -> list[MotionEvent]:
    events: list[MotionEvent] = []
    active_start_index: int | None = None
    peak_index: int | None = None
    last_available_index: int | None = None

    for index, sample in enumerate(samples):
        if active_start_index is None:
            if sample.available and sample.extension_ratio >= start_threshold:
                active_start_index = index
                peak_index = index
                last_available_index = index
            continue

        start = samples[active_start_index]
        if sample.available:
            last_available_index = index
            if peak_index is None or sample.extension_ratio > samples[peak_index].extension_ratio:
                peak_index = index

            duration_ms = sample.timestamp_ms - start.timestamp_ms
            if (
                sample.extension_ratio <= return_threshold
                and peak_index is not None
                and samples[peak_index].extension_ratio >= min_peak
                and duration_ms >= min_duration_ms
            ):
                events.append(
                    _hand_event(
                        event_type,
                        samples,
                        active_start_index,
                        peak_index,
                        index,
                        "returned",
                    )
                )
                active_start_index = None
                peak_index = None
                last_available_index = None
                continue

            if duration_ms > max_duration_ms and peak_index is not None:
                events.append(
                    _hand_event(
                        event_type,
                        samples,
                        active_start_index,
                        peak_index,
                        index,
                        "timeout",
                    )
                )
                active_start_index = None
                peak_index = None
                last_available_index = None
            continue

        if last_available_index is None:
            continue
        gap_ms = sample.timestamp_ms - samples[last_available_index].timestamp_ms
        if gap_ms > max_tracking_gap_ms and peak_index is not None:
            events.append(
                _hand_event(
                    event_type,
                    samples,
                    active_start_index,
                    peak_index,
                    last_available_index,
                    "lost_tracking",
                )
            )
            active_start_index = None
            peak_index = None
            last_available_index = None

    if active_start_index is not None and peak_index is not None:
        end_index = last_available_index if last_available_index is not None else len(samples) - 1
        if samples[peak_index].extension_ratio >= min_peak:
            events.append(
                _hand_event(
                    event_type,
                    samples,
                    active_start_index,
                    peak_index,
                    end_index,
                    "clip_end",
                )
            )
    return events


def _hand_event(
    event_type: EventType,
    samples: list[_HandSample],
    start_index: int,
    peak_index: int,
    end_index: int,
    end_reason: EventEndReason,
) -> MotionEvent:
    event_samples = samples[start_index : end_index + 1]
    available_count = sum(1 for sample in event_samples if sample.available)
    start = samples[start_index]
    peak = samples[peak_index]
    end = samples[end_index]
    return MotionEvent(
        event_type=event_type,
        start_ms=start.timestamp_ms,
        peak_ms=peak.timestamp_ms,
        end_ms=end.timestamp_ms,
        duration_ms=round(end.timestamp_ms - start.timestamp_ms, 1),
        peak_value=peak.extension_ratio,
        end_reason=end_reason,
        available_ratio=_ratio(available_count, len(event_samples)),
        frame_count=len(event_samples),
    )


def _detect_body_movement_events(
    samples: list[_MovementSample],
    calibration_profile: CalibrationProfile,
    min_duration_ms: float = 120.0,
    max_gap_ms: float = 250.0,
) -> list[MotionEvent]:
    baseline_sway = calibration_profile.movement_baseline.sway_radius_p95 or 0.0
    threshold = max(0.025, baseline_sway * 3.0)
    return_threshold = max(0.015, threshold * 0.6)
    events: list[MotionEvent] = []
    active_start_index: int | None = None
    peak_index: int | None = None
    last_available_index: int | None = None

    for index, sample in enumerate(samples):
        if active_start_index is None:
            if sample.available and sample.radius >= threshold:
                active_start_index = index
                peak_index = index
                last_available_index = index
            continue

        start = samples[active_start_index]
        if sample.available:
            last_available_index = index
            if peak_index is None or sample.radius > samples[peak_index].radius:
                peak_index = index

            duration_ms = sample.timestamp_ms - start.timestamp_ms
            if sample.radius <= return_threshold and duration_ms >= min_duration_ms:
                assert peak_index is not None
                events.append(
                    _movement_event(
                        samples,
                        active_start_index,
                        peak_index,
                        index,
                        "returned",
                    )
                )
                active_start_index = None
                peak_index = None
                last_available_index = None
            continue

        if last_available_index is None:
            continue
        gap_ms = sample.timestamp_ms - samples[last_available_index].timestamp_ms
        if gap_ms > max_gap_ms and peak_index is not None:
            events.append(
                _movement_event(
                    samples,
                    active_start_index,
                    peak_index,
                    last_available_index,
                    "lost_tracking",
                )
            )
            active_start_index = None
            peak_index = None
            last_available_index = None

    if active_start_index is not None and peak_index is not None:
        end_index = last_available_index if last_available_index is not None else len(samples) - 1
        events.append(
            _movement_event(samples, active_start_index, peak_index, end_index, "clip_end")
        )
    return events


def _movement_event(
    samples: list[_MovementSample],
    start_index: int,
    peak_index: int,
    end_index: int,
    end_reason: EventEndReason,
) -> MotionEvent:
    event_samples = samples[start_index : end_index + 1]
    available_count = sum(1 for sample in event_samples if sample.available)
    start = samples[start_index]
    peak = samples[peak_index]
    end = samples[end_index]
    return MotionEvent(
        event_type="body_movement",
        start_ms=start.timestamp_ms,
        peak_ms=peak.timestamp_ms,
        end_ms=end.timestamp_ms,
        duration_ms=round(end.timestamp_ms - start.timestamp_ms, 1),
        peak_value=peak.radius,
        end_reason=end_reason,
        available_ratio=_ratio(available_count, len(event_samples)),
        frame_count=len(event_samples),
        direction=_movement_direction(peak.dx, peak.dy),
    )


def _movement_direction(dx: float, dy: float) -> str:
    if abs(dx) >= abs(dy):
        return "screen_right" if dx > 0 else "screen_left"
    return "screen_down" if dy > 0 else "screen_up"


def _hip_center(frame: PoseFrame) -> tuple[float, float] | None:
    landmarks = frame.landmark_map()
    left_hip = _visible(landmarks.get("left_hip"))
    right_hip = _visible(landmarks.get("right_hip"))
    if left_hip is None or right_hip is None:
        return None
    return ((left_hip.x + right_hip.x) / 2.0, (left_hip.y + right_hip.y) / 2.0)


def _visible(landmark: Landmark | None, min_confidence: float = 0.35) -> Landmark | None:
    if landmark is None:
        return None
    if (landmark.confidence or 0.0) < min_confidence:
        return None
    return landmark


def _lead_side(stance: Stance) -> str:
    return "left" if stance == "orthodox" else "right"


def _rear_side(stance: Stance) -> str:
    return "right" if stance == "orthodox" else "left"


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 3)
