from dataclasses import asdict, dataclass
from math import sqrt
from statistics import mean
from typing import Any, Literal, cast

from analysis.pose import Landmark, PoseFrame

OrientationLabel = Literal[
    "front_readable",
    "angle_readable",
    "side_readable",
    "partially_occluded",
    "unreadable",
]

MIN_LANDMARK_CONFIDENCE = 0.35

TORSO_LANDMARKS = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]
HAND_LANDMARKS = ["left_elbow", "right_elbow", "left_wrist", "right_wrist"]
LEG_LANDMARKS = ["left_knee", "right_knee", "left_ankle", "right_ankle"]
FOOT_LANDMARKS = [
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]
CORE_LANDMARKS = TORSO_LANDMARKS + HAND_LANDMARKS + LEG_LANDMARKS


@dataclass(frozen=True)
class OrientationEstimate:
    # This is deliberately a rough "can we trust this angle?" estimate, not a
    # promise that we know the exact 3D body angle from one phone camera.
    label: OrientationLabel
    confidence: float
    shoulder_width: float | None
    hip_width: float | None
    body_height: float | None
    torso_width_to_height: float | None
    shoulder_z_delta: float | None
    hip_z_delta: float | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrameQuality:
    frame_index: int
    timestamp_ms: float
    pose_visible: bool
    core_visibility_ratio: float
    full_body_visible: bool
    hands_visible: bool
    feet_visible: bool
    torso_visible: bool
    average_confidence: float | None
    orientation: OrientationEstimate
    allowed_analyses: list[str]

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orientation"] = self.orientation.to_json()
        return payload


@dataclass(frozen=True)
class ClipQualitySummary:
    total_frames: int
    pose_visibility_ratio: float
    full_body_visibility_ratio: float
    hands_visibility_ratio: float
    feet_visibility_ratio: float
    torso_visibility_ratio: float
    average_core_visibility_ratio: float
    average_landmark_confidence: float | None
    orientation_counts: dict[str, int]
    dominant_orientation: OrientationLabel
    allowed_analysis_ratios: dict[str, float]
    landmark_visibility_ratios: dict[str, float]
    average_torso_width_to_height: float | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def analyze_frame_quality(
    frame: PoseFrame,
    min_confidence: float = MIN_LANDMARK_CONFIDENCE,
) -> FrameQuality:
    landmarks = frame.landmark_map()
    pose_visible = bool(frame.landmarks)
    core_visibility_ratio = _visibility_ratio(landmarks, CORE_LANDMARKS, min_confidence)
    torso_visible = _all_visible(landmarks, TORSO_LANDMARKS, min_confidence)
    hands_visible = _all_visible(landmarks, HAND_LANDMARKS, min_confidence)
    feet_visible = _all_visible(landmarks, FOOT_LANDMARKS, min_confidence)
    full_body_visible = torso_visible and hands_visible and feet_visible
    average_confidence = _average_confidence(landmarks, CORE_LANDMARKS, min_confidence)
    orientation = estimate_orientation(frame, min_confidence=min_confidence)

    return FrameQuality(
        frame_index=frame.frame_index,
        timestamp_ms=frame.timestamp_ms,
        pose_visible=pose_visible,
        core_visibility_ratio=core_visibility_ratio,
        full_body_visible=full_body_visible,
        hands_visible=hands_visible,
        feet_visible=feet_visible,
        torso_visible=torso_visible,
        average_confidence=average_confidence,
        orientation=orientation,
        allowed_analyses=_allowed_analyses(
            torso_visible=torso_visible,
            hands_visible=hands_visible,
            feet_visible=feet_visible,
            orientation=orientation.label,
        ),
    )


def summarize_clip_quality(
    frames: list[PoseFrame],
    min_confidence: float = MIN_LANDMARK_CONFIDENCE,
) -> ClipQualitySummary:
    qualities = [
        analyze_frame_quality(frame, min_confidence=min_confidence)
        for frame in frames
    ]
    total_frames = len(qualities)
    if total_frames == 0:
        return ClipQualitySummary(
            total_frames=0,
            pose_visibility_ratio=0.0,
            full_body_visibility_ratio=0.0,
            hands_visibility_ratio=0.0,
            feet_visibility_ratio=0.0,
            torso_visibility_ratio=0.0,
            average_core_visibility_ratio=0.0,
            average_landmark_confidence=None,
            orientation_counts={},
            dominant_orientation="unreadable",
            allowed_analysis_ratios={},
            landmark_visibility_ratios={},
            average_torso_width_to_height=None,
        )

    orientation_counts: dict[str, int] = {}
    allowed_counts: dict[str, int] = {}
    confidences: list[float] = []
    torso_ratios: list[float] = []

    for quality in qualities:
        label = quality.orientation.label
        orientation_counts[label] = orientation_counts.get(label, 0) + 1
        for analysis_name in quality.allowed_analyses:
            allowed_counts[analysis_name] = allowed_counts.get(analysis_name, 0) + 1
        if quality.average_confidence is not None:
            confidences.append(quality.average_confidence)
        if quality.orientation.torso_width_to_height is not None:
            torso_ratios.append(quality.orientation.torso_width_to_height)

    dominant_orientation = cast(
        OrientationLabel,
        max(
            orientation_counts,
            key=lambda label: orientation_counts[label],
            default="unreadable",
        ),
    )

    return ClipQualitySummary(
        total_frames=total_frames,
        pose_visibility_ratio=_ratio(
            sum(1 for quality in qualities if quality.pose_visible),
            total_frames,
        ),
        full_body_visibility_ratio=_ratio(
            sum(1 for quality in qualities if quality.full_body_visible),
            total_frames,
        ),
        hands_visibility_ratio=_ratio(
            sum(1 for quality in qualities if quality.hands_visible),
            total_frames,
        ),
        feet_visibility_ratio=_ratio(
            sum(1 for quality in qualities if quality.feet_visible),
            total_frames,
        ),
        torso_visibility_ratio=_ratio(
            sum(1 for quality in qualities if quality.torso_visible),
            total_frames,
        ),
        average_core_visibility_ratio=round(
            mean(quality.core_visibility_ratio for quality in qualities),
            3,
        ),
        average_landmark_confidence=round(mean(confidences), 3) if confidences else None,
        orientation_counts=orientation_counts,
        dominant_orientation=dominant_orientation,
        allowed_analysis_ratios={
            name: _ratio(count, total_frames) for name, count in sorted(allowed_counts.items())
        },
        landmark_visibility_ratios=_landmark_visibility_ratios(
            frames,
            CORE_LANDMARKS + FOOT_LANDMARKS,
            min_confidence,
        ),
        average_torso_width_to_height=(
            round(mean(torso_ratios), 3) if torso_ratios else None
        ),
    )


def estimate_orientation(
    frame: PoseFrame,
    min_confidence: float = MIN_LANDMARK_CONFIDENCE,
) -> OrientationEstimate:
    landmarks = frame.landmark_map()
    left_shoulder = _visible(landmarks.get("left_shoulder"), min_confidence)
    right_shoulder = _visible(landmarks.get("right_shoulder"), min_confidence)
    left_hip = _visible(landmarks.get("left_hip"), min_confidence)
    right_hip = _visible(landmarks.get("right_hip"), min_confidence)

    visible_torso_landmarks = [
        landmark for landmark in [left_shoulder, right_shoulder, left_hip, right_hip]
        if landmark is not None
    ]
    if not visible_torso_landmarks:
        return OrientationEstimate("unreadable", 0.0, None, None, None, None, None, None)

    if len(visible_torso_landmarks) < 4:
        return OrientationEstimate(
            "partially_occluded",
            round(len(visible_torso_landmarks) / 4.0, 3),
            None,
            None,
            _body_height(landmarks, min_confidence),
            None,
            None,
            None,
        )

    assert left_shoulder is not None
    assert right_shoulder is not None
    assert left_hip is not None
    assert right_hip is not None

    shoulder_width = abs(left_shoulder.x - right_shoulder.x)
    hip_width = abs(left_hip.x - right_hip.x)
    body_height = _body_height(landmarks, min_confidence)
    torso_width = mean([shoulder_width, hip_width])
    torso_width_to_height = torso_width / body_height if body_height and body_height > 0 else None
    shoulder_z_delta = _z_delta(left_shoulder, right_shoulder)
    hip_z_delta = _z_delta(left_hip, right_hip)

    if torso_width_to_height is None:
        label: OrientationLabel = "unreadable"
        confidence = 0.1
    elif torso_width_to_height >= 0.22:
        label = "front_readable"
        confidence = 0.85
    elif torso_width_to_height >= 0.11:
        label = "angle_readable"
        confidence = 0.8
    elif torso_width_to_height >= 0.045:
        label = "side_readable"
        confidence = 0.6
    else:
        label = "partially_occluded"
        confidence = 0.35

    return OrientationEstimate(
        label=label,
        confidence=round(confidence, 3),
        shoulder_width=round(shoulder_width, 3),
        hip_width=round(hip_width, 3),
        body_height=round(body_height, 3) if body_height is not None else None,
        torso_width_to_height=(
            round(torso_width_to_height, 3) if torso_width_to_height is not None else None
        ),
        shoulder_z_delta=shoulder_z_delta,
        hip_z_delta=hip_z_delta,
    )


def _allowed_analyses(
    torso_visible: bool,
    hands_visible: bool,
    feet_visible: bool,
    orientation: OrientationLabel,
) -> list[str]:
    if not torso_visible or orientation == "unreadable":
        return []

    allowed = ["orientation"]
    if orientation != "partially_occluded" and hands_visible:
        allowed.extend(["guard", "upper_body_strikes"])
    if feet_visible:
        allowed.append("movement")
    if hands_visible and feet_visible and orientation in {"front_readable", "angle_readable"}:
        allowed.append("full_form")
    return allowed


def _visible(landmark: Landmark | None, min_confidence: float) -> Landmark | None:
    if landmark is None:
        return None
    if (landmark.confidence or 0.0) < min_confidence:
        return None
    return landmark


def _all_visible(
    landmarks: dict[str, Landmark],
    names: list[str],
    min_confidence: float,
) -> bool:
    return all(_visible(landmarks.get(name), min_confidence) is not None for name in names)


def _visibility_ratio(
    landmarks: dict[str, Landmark],
    names: list[str],
    min_confidence: float,
) -> float:
    visible_count = sum(
        1 for name in names if _visible(landmarks.get(name), min_confidence) is not None
    )
    return _ratio(visible_count, len(names))


def _landmark_visibility_ratios(
    frames: list[PoseFrame],
    names: list[str],
    min_confidence: float,
) -> dict[str, float]:
    total_frames = len(frames)
    unique_names = sorted(set(names))
    counts = dict.fromkeys(unique_names, 0)
    for frame in frames:
        landmarks = frame.landmark_map()
        for name in unique_names:
            if _visible(landmarks.get(name), min_confidence) is not None:
                counts[name] += 1
    return {name: _ratio(count, total_frames) for name, count in counts.items()}


def _average_confidence(
    landmarks: dict[str, Landmark],
    names: list[str],
    min_confidence: float,
) -> float | None:
    confidences = [
        landmark.confidence or 0.0
        for name in names
        if (landmark := _visible(landmarks.get(name), min_confidence)) is not None
    ]
    return round(mean(confidences), 3) if confidences else None


def _body_height(
    landmarks: dict[str, Landmark],
    min_confidence: float,
) -> float | None:
    names = [
        "nose",
        "left_eye",
        "right_eye",
        "left_shoulder",
        "right_shoulder",
        "left_ankle",
        "right_ankle",
        "left_heel",
        "right_heel",
        "left_foot_index",
        "right_foot_index",
    ]
    visible = [
        landmark
        for name in names
        if (landmark := _visible(landmarks.get(name), min_confidence)) is not None
    ]
    if len(visible) < 2:
        return None
    return max(landmark.y for landmark in visible) - min(landmark.y for landmark in visible)


def _z_delta(first: Landmark, second: Landmark) -> float | None:
    if first.z is None or second.z is None:
        return None
    return round(first.z - second.z, 3)


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 3)


def distance_2d(first: Landmark, second: Landmark) -> float:
    return sqrt((first.x - second.x) ** 2 + (first.y - second.y) ** 2)
