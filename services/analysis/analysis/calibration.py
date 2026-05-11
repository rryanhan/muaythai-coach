from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Literal

from analysis.pose import Landmark, PoseFrame
from analysis.quality import ClipQualitySummary, distance_2d, summarize_clip_quality

Stance = Literal["orthodox", "southpaw"]


@dataclass(frozen=True)
class GuardBaseline:
    # Wrist positions are stored relative to the matching shoulder so the numbers
    # survive small framing changes better than raw image coordinates.
    lead_wrist_from_shoulder_x: float | None
    lead_wrist_from_shoulder_y: float | None
    rear_wrist_from_shoulder_x: float | None
    rear_wrist_from_shoulder_y: float | None
    lead_shoulder_to_wrist_distance: float | None
    rear_shoulder_to_wrist_distance: float | None
    sample_count: int


@dataclass(frozen=True)
class ReachBaseline:
    guard_distance: float | None
    max_distance: float | None
    travel_distance: float | None
    guard_horizontal_extension: float | None
    max_horizontal_extension: float | None
    horizontal_travel: float | None
    sample_count: int


@dataclass(frozen=True)
class StanceBaseline:
    hip_center_x: float | None
    hip_center_y: float | None
    shoulder_center_x: float | None
    shoulder_center_y: float | None
    ankle_width: float | None
    body_height: float | None
    sample_count: int


@dataclass(frozen=True)
class MovementBaseline:
    sway_x_p95: float | None
    sway_y_p95: float | None
    sway_radius_p95: float | None
    sample_count: int


@dataclass(frozen=True)
class CalibrationProfile:
    dataset: str
    stance: Stance
    source_files: list[str]
    visibility: dict[str, Any]
    orientation: dict[str, Any]
    guard: GuardBaseline
    lead_reach: ReachBaseline
    rear_reach: ReachBaseline
    stance_baseline: StanceBaseline
    movement_baseline: MovementBaseline

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def build_calibration_profile(
    *,
    dataset: str,
    stance: Stance,
    source_files: list[str],
    full_body_frames: list[PoseFrame],
    lead_reach_frames: list[PoseFrame],
    rear_reach_frames: list[PoseFrame],
    movement_baseline_frames: list[PoseFrame],
) -> CalibrationProfile:
    full_body_quality = summarize_clip_quality(full_body_frames)
    guard = _guard_baseline(
        stance=stance,
        full_body_frames=full_body_frames,
        lead_reach_frames=lead_reach_frames,
        rear_reach_frames=rear_reach_frames,
    )
    lead_reach = _reach_baseline(
        frames=lead_reach_frames,
        wrist_name=_lead_wrist_name(stance),
        shoulder_name=_lead_shoulder_name(stance),
        guard_distance=guard.lead_shoulder_to_wrist_distance,
        guard_horizontal_extension=(
            abs(guard.lead_wrist_from_shoulder_x)
            if guard.lead_wrist_from_shoulder_x is not None
            else None
        ),
    )
    rear_reach = _reach_baseline(
        frames=rear_reach_frames,
        wrist_name=_rear_wrist_name(stance),
        shoulder_name=_rear_shoulder_name(stance),
        guard_distance=guard.rear_shoulder_to_wrist_distance,
        guard_horizontal_extension=(
            abs(guard.rear_wrist_from_shoulder_x)
            if guard.rear_wrist_from_shoulder_x is not None
            else None
        ),
    )

    return CalibrationProfile(
        dataset=dataset,
        stance=stance,
        source_files=source_files,
        visibility=_visibility_payload(full_body_quality),
        orientation=_orientation_payload(full_body_quality),
        guard=guard,
        lead_reach=lead_reach,
        rear_reach=rear_reach,
        stance_baseline=_stance_baseline(full_body_frames),
        movement_baseline=_movement_baseline(movement_baseline_frames),
    )


def _visibility_payload(summary: ClipQualitySummary) -> dict[str, Any]:
    return {
        "pose_visibility_ratio": summary.pose_visibility_ratio,
        "full_body_visibility_ratio": summary.full_body_visibility_ratio,
        "hands_visibility_ratio": summary.hands_visibility_ratio,
        "feet_visibility_ratio": summary.feet_visibility_ratio,
        "torso_visibility_ratio": summary.torso_visibility_ratio,
        "average_core_visibility_ratio": summary.average_core_visibility_ratio,
        "average_landmark_confidence": summary.average_landmark_confidence,
    }


def _orientation_payload(summary: ClipQualitySummary) -> dict[str, Any]:
    return {
        "dominant_orientation": summary.dominant_orientation,
        "orientation_counts": summary.orientation_counts,
        "average_torso_width_to_height": summary.average_torso_width_to_height,
    }


def _guard_baseline(
    *,
    stance: Stance,
    full_body_frames: list[PoseFrame],
    lead_reach_frames: list[PoseFrame],
    rear_reach_frames: list[PoseFrame],
) -> GuardBaseline:
    lead_samples = _wrist_samples(
        frames=_guard_frames(full_body_frames) + _first_fraction(lead_reach_frames, 0.25),
        wrist_name=_lead_wrist_name(stance),
        shoulder_name=_lead_shoulder_name(stance),
    )
    rear_samples = _wrist_samples(
        frames=_guard_frames(full_body_frames) + _first_fraction(rear_reach_frames, 0.25),
        wrist_name=_rear_wrist_name(stance),
        shoulder_name=_rear_shoulder_name(stance),
    )
    sample_count = min(len(lead_samples), len(rear_samples))
    return GuardBaseline(
        lead_wrist_from_shoulder_x=_sample_mean(lead_samples, "x_offset"),
        lead_wrist_from_shoulder_y=_sample_mean(lead_samples, "y_offset"),
        rear_wrist_from_shoulder_x=_sample_mean(rear_samples, "x_offset"),
        rear_wrist_from_shoulder_y=_sample_mean(rear_samples, "y_offset"),
        lead_shoulder_to_wrist_distance=_sample_mean(lead_samples, "distance"),
        rear_shoulder_to_wrist_distance=_sample_mean(rear_samples, "distance"),
        sample_count=sample_count,
    )


def _reach_baseline(
    *,
    frames: list[PoseFrame],
    wrist_name: str,
    shoulder_name: str,
    guard_distance: float | None,
    guard_horizontal_extension: float | None,
) -> ReachBaseline:
    samples = _wrist_samples(frames, wrist_name, shoulder_name)
    distances = [sample["distance"] for sample in samples]
    horizontal_extensions = [abs(sample["x_offset"]) for sample in samples]
    max_distance = _percentile(distances, 0.95)
    max_horizontal_extension = _percentile(horizontal_extensions, 0.95)
    return ReachBaseline(
        guard_distance=guard_distance,
        max_distance=max_distance,
        travel_distance=(
            _rounded(max_distance - guard_distance)
            if max_distance is not None and guard_distance is not None
            else None
        ),
        guard_horizontal_extension=guard_horizontal_extension,
        max_horizontal_extension=max_horizontal_extension,
        horizontal_travel=(
            _rounded(max_horizontal_extension - guard_horizontal_extension)
            if max_horizontal_extension is not None and guard_horizontal_extension is not None
            else None
        ),
        sample_count=len(samples),
    )


def _stance_baseline(frames: list[PoseFrame]) -> StanceBaseline:
    samples = [_body_sample(frame) for frame in frames]
    valid_samples = [sample for sample in samples if sample is not None]
    return StanceBaseline(
        hip_center_x=_sample_mean(valid_samples, "hip_center_x"),
        hip_center_y=_sample_mean(valid_samples, "hip_center_y"),
        shoulder_center_x=_sample_mean(valid_samples, "shoulder_center_x"),
        shoulder_center_y=_sample_mean(valid_samples, "shoulder_center_y"),
        ankle_width=_sample_mean(valid_samples, "ankle_width"),
        body_height=_sample_mean(valid_samples, "body_height"),
        sample_count=len(valid_samples),
    )


def _movement_baseline(frames: list[PoseFrame]) -> MovementBaseline:
    centers = [_hip_center(frame) for frame in frames]
    valid_centers = [center for center in centers if center is not None]
    if not valid_centers:
        return MovementBaseline(None, None, None, 0)

    center_x = mean(center[0] for center in valid_centers)
    center_y = mean(center[1] for center in valid_centers)
    x_offsets = [abs(center[0] - center_x) for center in valid_centers]
    y_offsets = [abs(center[1] - center_y) for center in valid_centers]
    radii = [
        ((center[0] - center_x) ** 2 + (center[1] - center_y) ** 2) ** 0.5
        for center in valid_centers
    ]
    return MovementBaseline(
        sway_x_p95=_percentile(x_offsets, 0.95),
        sway_y_p95=_percentile(y_offsets, 0.95),
        sway_radius_p95=_percentile(radii, 0.95),
        sample_count=len(valid_centers),
    )


def _wrist_samples(
    frames: list[PoseFrame],
    wrist_name: str,
    shoulder_name: str,
) -> list[dict[str, float]]:
    samples: list[dict[str, float]] = []
    for frame in frames:
        landmarks = frame.landmark_map()
        wrist = _visible(landmarks.get(wrist_name))
        shoulder = _visible(landmarks.get(shoulder_name))
        if wrist is None or shoulder is None:
            continue
        samples.append(
            {
                "x_offset": _rounded(wrist.x - shoulder.x),
                "y_offset": _rounded(wrist.y - shoulder.y),
                "distance": _rounded(distance_2d(wrist, shoulder)),
            }
        )
    return samples


def _body_sample(frame: PoseFrame) -> dict[str, float] | None:
    landmarks = frame.landmark_map()
    left_shoulder = _visible(landmarks.get("left_shoulder"))
    right_shoulder = _visible(landmarks.get("right_shoulder"))
    left_hip = _visible(landmarks.get("left_hip"))
    right_hip = _visible(landmarks.get("right_hip"))
    left_ankle = _visible(landmarks.get("left_ankle"))
    right_ankle = _visible(landmarks.get("right_ankle"))
    if not all([left_shoulder, right_shoulder, left_hip, right_hip, left_ankle, right_ankle]):
        return None

    assert left_shoulder is not None
    assert right_shoulder is not None
    assert left_hip is not None
    assert right_hip is not None
    assert left_ankle is not None
    assert right_ankle is not None

    highest = min(left_shoulder.y, right_shoulder.y)
    lowest = max(left_ankle.y, right_ankle.y)
    return {
        "hip_center_x": _rounded((left_hip.x + right_hip.x) / 2.0),
        "hip_center_y": _rounded((left_hip.y + right_hip.y) / 2.0),
        "shoulder_center_x": _rounded((left_shoulder.x + right_shoulder.x) / 2.0),
        "shoulder_center_y": _rounded((left_shoulder.y + right_shoulder.y) / 2.0),
        "ankle_width": _rounded(abs(left_ankle.x - right_ankle.x)),
        "body_height": _rounded(lowest - highest),
    }


def _hip_center(frame: PoseFrame) -> tuple[float, float] | None:
    landmarks = frame.landmark_map()
    left_hip = _visible(landmarks.get("left_hip"))
    right_hip = _visible(landmarks.get("right_hip"))
    if left_hip is None or right_hip is None:
        return None
    return ((left_hip.x + right_hip.x) / 2.0, (left_hip.y + right_hip.y) / 2.0)


def _guard_frames(frames: list[PoseFrame]) -> list[PoseFrame]:
    # The full-body calibration clip should mostly be guard, but using the first
    # half is safer if the user moves at the end.
    return _first_fraction(frames, 0.5)


def _first_fraction(frames: list[PoseFrame], fraction: float) -> list[PoseFrame]:
    if not frames:
        return []
    count = max(1, int(len(frames) * fraction))
    return frames[:count]


def _sample_mean(samples: list[dict[str, float]], field: str) -> float | None:
    values = [sample[field] for sample in samples if field in sample]
    return _rounded(mean(values)) if values else None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return _rounded(ordered[index])


def _visible(landmark: Landmark | None, min_confidence: float = 0.35) -> Landmark | None:
    if landmark is None:
        return None
    if (landmark.confidence or 0.0) < min_confidence:
        return None
    return landmark


def _rounded(value: float) -> float:
    return round(value, 3)


def _lead_wrist_name(stance: Stance) -> str:
    return "left_wrist" if stance == "orthodox" else "right_wrist"


def _rear_wrist_name(stance: Stance) -> str:
    return "right_wrist" if stance == "orthodox" else "left_wrist"


def _lead_shoulder_name(stance: Stance) -> str:
    return "left_shoulder" if stance == "orthodox" else "right_shoulder"


def _rear_shoulder_name(stance: Stance) -> str:
    return "right_shoulder" if stance == "orthodox" else "left_shoulder"
