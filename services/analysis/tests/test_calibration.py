from analysis.calibration import build_calibration_profile
from analysis.pose import Landmark, PoseFrame


def test_build_calibration_profile_uses_reach_and_movement_clips() -> None:
    full_body_frames = [_frame(0, 0.0, left_wrist_x=0.36, right_wrist_x=0.64)]
    lead_reach_frames = [
        _frame(1, 33.0, left_wrist_x=0.36, right_wrist_x=0.64),
        _frame(2, 66.0, left_wrist_x=0.24, right_wrist_x=0.64),
        _frame(3, 99.0, left_wrist_x=0.18, right_wrist_x=0.64),
    ]
    rear_reach_frames = [
        _frame(4, 132.0, left_wrist_x=0.36, right_wrist_x=0.64),
        _frame(5, 165.0, left_wrist_x=0.36, right_wrist_x=0.74),
        _frame(6, 198.0, left_wrist_x=0.36, right_wrist_x=0.82),
    ]
    movement_frames = [
        _frame(7, 231.0, left_wrist_x=0.36, right_wrist_x=0.64, hip_shift=0.0),
        _frame(8, 264.0, left_wrist_x=0.36, right_wrist_x=0.64, hip_shift=0.02),
    ]

    profile = build_calibration_profile(
        dataset="test_dataset",
        stance="orthodox",
        source_files=["calibration_good_full_body_orthodox.MOV"],
        full_body_frames=full_body_frames,
        lead_reach_frames=lead_reach_frames,
        rear_reach_frames=rear_reach_frames,
        movement_baseline_frames=movement_frames,
    )

    assert profile.dataset == "test_dataset"
    assert profile.guard.sample_count >= 1
    assert profile.lead_reach.travel_distance is not None
    assert profile.lead_reach.travel_distance > 0
    assert profile.rear_reach.travel_distance is not None
    assert profile.rear_reach.travel_distance > 0
    assert profile.movement_baseline.sample_count == 2


def _frame(
    frame_index: int,
    timestamp_ms: float,
    *,
    left_wrist_x: float,
    right_wrist_x: float,
    hip_shift: float = 0.0,
) -> PoseFrame:
    left_hip_x = 0.43 + hip_shift
    right_hip_x = 0.57 + hip_shift
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        landmarks=[
            Landmark("nose", 0.5, 0.1, 0.0, 0.95),
            Landmark("left_shoulder", 0.42, 0.25, 0.0, 0.95),
            Landmark("right_shoulder", 0.58, 0.25, 0.0, 0.95),
            Landmark("left_elbow", 0.38, 0.36, 0.0, 0.95),
            Landmark("right_elbow", 0.62, 0.36, 0.0, 0.95),
            Landmark("left_wrist", left_wrist_x, 0.42, 0.0, 0.95),
            Landmark("right_wrist", right_wrist_x, 0.42, 0.0, 0.95),
            Landmark("left_hip", left_hip_x, 0.55, 0.0, 0.95),
            Landmark("right_hip", right_hip_x, 0.55, 0.0, 0.95),
            Landmark("left_knee", 0.42 + hip_shift, 0.7, 0.0, 0.95),
            Landmark("right_knee", 0.58 + hip_shift, 0.7, 0.0, 0.95),
            Landmark("left_ankle", 0.4 + hip_shift, 0.85, 0.0, 0.95),
            Landmark("right_ankle", 0.6 + hip_shift, 0.85, 0.0, 0.95),
            Landmark("left_heel", 0.39 + hip_shift, 0.88, 0.0, 0.95),
            Landmark("right_heel", 0.61 + hip_shift, 0.88, 0.0, 0.95),
            Landmark("left_foot_index", 0.38 + hip_shift, 0.9, 0.0, 0.95),
            Landmark("right_foot_index", 0.62 + hip_shift, 0.9, 0.0, 0.95),
        ],
    )
