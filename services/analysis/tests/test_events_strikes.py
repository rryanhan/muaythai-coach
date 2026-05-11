from analysis.calibration import (
    CalibrationProfile,
    GuardBaseline,
    MovementBaseline,
    ReachBaseline,
    StanceBaseline,
)
from analysis.events import detect_motion_events
from analysis.gating import build_frame_gates
from analysis.pose import Landmark, PoseFrame
from analysis.strikes import analyze_straight_strikes


def test_detects_lead_hand_motion_as_jab() -> None:
    frames = [
        _frame(0, 0.0, left_wrist_x=0.45),
        _frame(1, 50.0, left_wrist_x=0.6),
        _frame(2, 100.0, left_wrist_x=0.72),
        _frame(3, 150.0, left_wrist_x=0.6),
        _frame(4, 200.0, left_wrist_x=0.45),
    ]
    gates = build_frame_gates(frames, stance="orthodox")

    events = detect_motion_events(frames, gates, _profile(), stance="orthodox")
    strikes = analyze_straight_strikes(events)

    assert events.counts_by_type["lead_hand_motion"] == 1
    assert strikes.high_or_medium_counts["jab"] == 1
    assert strikes.high_or_medium_counts["cross"] == 0
    assert strikes.strikes[0].returned_to_guard is True


def _profile() -> CalibrationProfile:
    return CalibrationProfile(
        dataset="test",
        stance="orthodox",
        source_files=[],
        visibility={},
        orientation={},
        guard=GuardBaseline(0.05, 0.0, 0.05, 0.0, 0.05, 0.05, 5),
        lead_reach=ReachBaseline(0.05, 0.35, 0.3, 0.05, 0.35, 0.3, 5),
        rear_reach=ReachBaseline(0.05, 0.35, 0.3, 0.05, 0.35, 0.3, 5),
        stance_baseline=StanceBaseline(0.5, 0.55, 0.5, 0.25, 0.2, 0.6, 5),
        movement_baseline=MovementBaseline(0.005, 0.005, 0.008, 5),
    )


def _frame(frame_index: int, timestamp_ms: float, left_wrist_x: float) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        landmarks=[
            Landmark("nose", 0.5, 0.1, 0.0, 0.95),
            Landmark("left_shoulder", 0.42, 0.25, 0.0, 0.95),
            Landmark("right_shoulder", 0.58, 0.25, 0.0, 0.95),
            Landmark("left_elbow", 0.5, 0.32, 0.0, 0.95),
            Landmark("right_elbow", 0.62, 0.36, 0.0, 0.95),
            Landmark("left_wrist", left_wrist_x, 0.25, 0.0, 0.95),
            Landmark("right_wrist", 0.64, 0.42, 0.0, 0.95),
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
        ],
    )
