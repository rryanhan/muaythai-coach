from analysis.gating import build_frame_gate, summarize_frame_gates
from analysis.pose import Landmark, PoseFrame


def test_frame_gate_marks_rear_hand_unavailable() -> None:
    frame = _frame(include_rear_wrist=False)

    gate = build_frame_gate(frame, stance="orthodox")

    assert gate.lead_hand_available is True
    assert gate.rear_hand_available is False
    assert "rear_hand_unavailable" in gate.suppressed_reasons


def test_gate_summary_counts_available_ratios() -> None:
    gates = [
        build_frame_gate(_frame(include_rear_wrist=True), stance="orthodox"),
        build_frame_gate(_frame(include_rear_wrist=False), stance="orthodox"),
    ]

    summary = summarize_frame_gates(gates)

    assert summary.total_frames == 2
    assert summary.lead_hand_available_ratio == 1.0
    assert summary.rear_hand_available_ratio == 0.5


def _frame(include_rear_wrist: bool) -> PoseFrame:
    landmarks = [
        Landmark("nose", 0.5, 0.1, 0.0, 0.95),
        Landmark("left_shoulder", 0.42, 0.25, 0.0, 0.95),
        Landmark("right_shoulder", 0.58, 0.25, 0.0, 0.95),
        Landmark("left_elbow", 0.38, 0.36, 0.0, 0.95),
        Landmark("right_elbow", 0.62, 0.36, 0.0, 0.95),
        Landmark("left_wrist", 0.36, 0.42, 0.0, 0.95),
        Landmark("left_hip", 0.43, 0.55, 0.0, 0.95),
        Landmark("right_hip", 0.57, 0.55, 0.0, 0.95),
        Landmark("left_knee", 0.42, 0.7, 0.0, 0.95),
        Landmark("right_knee", 0.58, 0.7, 0.0, 0.95),
        Landmark("left_ankle", 0.4, 0.85, 0.0, 0.95),
        Landmark("right_ankle", 0.6, 0.85, 0.0, 0.95),
        Landmark("left_heel", 0.39, 0.88, 0.0, 0.95),
        Landmark("right_heel", 0.61, 0.88, 0.0, 0.95),
        Landmark("left_foot_index", 0.38, 0.9, 0.0, 0.95),
        Landmark("right_foot_index", 0.62, 0.9, 0.0, 0.95),
    ]
    if include_rear_wrist:
        landmarks.append(Landmark("right_wrist", 0.64, 0.42, 0.0, 0.95))
    return PoseFrame(frame_index=0, timestamp_ms=0.0, landmarks=landmarks)
