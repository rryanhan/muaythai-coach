from dataclasses import asdict, dataclass
from typing import Any

from analysis.calibration import Stance
from analysis.pose import Landmark, PoseFrame
from analysis.quality import MIN_LANDMARK_CONFIDENCE, OrientationLabel, analyze_frame_quality


@dataclass(frozen=True)
class FrameGate:
    # FrameGate answers "what are we allowed to judge in this frame?"
    # It deliberately avoids saying what happened; that belongs to events/strikes.
    frame_index: int
    timestamp_ms: float
    lead_hand_available: bool
    rear_hand_available: bool
    feet_available: bool
    torso_available: bool
    movement_available: bool
    upper_body_available: bool
    full_form_available: bool
    orientation_label: OrientationLabel
    orientation_confidence: float
    suppressed_reasons: list[str]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GateSummary:
    total_frames: int
    lead_hand_available_ratio: float
    rear_hand_available_ratio: float
    feet_available_ratio: float
    torso_available_ratio: float
    movement_available_ratio: float
    upper_body_available_ratio: float
    full_form_available_ratio: float
    suppression_counts: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def build_frame_gates(
    frames: list[PoseFrame],
    stance: Stance,
    min_confidence: float = MIN_LANDMARK_CONFIDENCE,
) -> list[FrameGate]:
    return [
        build_frame_gate(frame, stance=stance, min_confidence=min_confidence)
        for frame in frames
    ]


def build_frame_gate(
    frame: PoseFrame,
    stance: Stance,
    min_confidence: float = MIN_LANDMARK_CONFIDENCE,
) -> FrameGate:
    quality = analyze_frame_quality(frame, min_confidence=min_confidence)
    landmarks = frame.landmark_map()
    orientation_readable = quality.orientation.label not in {"unreadable", "partially_occluded"}
    lead_hand_available = _arm_available(landmarks, _lead_side(stance), min_confidence)
    rear_hand_available = _arm_available(landmarks, _rear_side(stance), min_confidence)
    torso_available = quality.torso_visible and quality.orientation.label != "unreadable"
    feet_available = quality.feet_visible
    movement_available = torso_available and feet_available
    upper_body_available = torso_available and orientation_readable and (
        lead_hand_available or rear_hand_available
    )
    full_form_available = (
        torso_available
        and orientation_readable
        and lead_hand_available
        and rear_hand_available
        and feet_available
        and quality.orientation.label in {"front_readable", "angle_readable"}
    )

    suppressed_reasons = _suppressed_reasons(
        lead_hand_available=lead_hand_available,
        rear_hand_available=rear_hand_available,
        feet_available=feet_available,
        torso_available=torso_available,
        orientation_label=quality.orientation.label,
    )

    return FrameGate(
        frame_index=frame.frame_index,
        timestamp_ms=frame.timestamp_ms,
        lead_hand_available=lead_hand_available,
        rear_hand_available=rear_hand_available,
        feet_available=feet_available,
        torso_available=torso_available,
        movement_available=movement_available,
        upper_body_available=upper_body_available,
        full_form_available=full_form_available,
        orientation_label=quality.orientation.label,
        orientation_confidence=quality.orientation.confidence,
        suppressed_reasons=suppressed_reasons,
    )


def summarize_frame_gates(gates: list[FrameGate]) -> GateSummary:
    total_frames = len(gates)
    suppression_counts: dict[str, int] = {}
    for gate in gates:
        for reason in gate.suppressed_reasons:
            suppression_counts[reason] = suppression_counts.get(reason, 0) + 1

    return GateSummary(
        total_frames=total_frames,
        lead_hand_available_ratio=_ratio(
            sum(1 for gate in gates if gate.lead_hand_available),
            total_frames,
        ),
        rear_hand_available_ratio=_ratio(
            sum(1 for gate in gates if gate.rear_hand_available),
            total_frames,
        ),
        feet_available_ratio=_ratio(
            sum(1 for gate in gates if gate.feet_available),
            total_frames,
        ),
        torso_available_ratio=_ratio(
            sum(1 for gate in gates if gate.torso_available),
            total_frames,
        ),
        movement_available_ratio=_ratio(
            sum(1 for gate in gates if gate.movement_available),
            total_frames,
        ),
        upper_body_available_ratio=_ratio(
            sum(1 for gate in gates if gate.upper_body_available),
            total_frames,
        ),
        full_form_available_ratio=_ratio(
            sum(1 for gate in gates if gate.full_form_available),
            total_frames,
        ),
        suppression_counts=dict(sorted(suppression_counts.items())),
    )


def _arm_available(
    landmarks: dict[str, Landmark],
    side: str,
    min_confidence: float,
) -> bool:
    return all(
        _visible(landmarks.get(f"{side}_{name}"), min_confidence) is not None
        for name in ["shoulder", "elbow", "wrist"]
    )


def _suppressed_reasons(
    *,
    lead_hand_available: bool,
    rear_hand_available: bool,
    feet_available: bool,
    torso_available: bool,
    orientation_label: OrientationLabel,
) -> list[str]:
    reasons: list[str] = []
    if not torso_available:
        reasons.append("torso_unavailable")
    if orientation_label in {"unreadable", "partially_occluded"}:
        reasons.append("orientation_low_trust")
    if not lead_hand_available:
        reasons.append("lead_hand_unavailable")
    if not rear_hand_available:
        reasons.append("rear_hand_unavailable")
    if not feet_available:
        reasons.append("feet_unavailable")
    return reasons


def _visible(landmark: Landmark | None, min_confidence: float) -> Landmark | None:
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
