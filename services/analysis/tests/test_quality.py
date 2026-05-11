from analysis.pose import Landmark, PoseFrame
from analysis.quality import analyze_frame_quality, summarize_clip_quality


def test_frame_quality_marks_full_body_and_allowed_analyses() -> None:
    frame = _full_body_frame(0, 0.0)

    quality = analyze_frame_quality(frame)

    assert quality.full_body_visible is True
    assert quality.hands_visible is True
    assert quality.feet_visible is True
    assert quality.orientation.label == "angle_readable"
    assert "upper_body_strikes" in quality.allowed_analyses
    assert "movement" in quality.allowed_analyses


def test_clip_quality_summarizes_visibility_ratios() -> None:
    frames = [
        _full_body_frame(0, 0.0),
        PoseFrame(frame_index=1, timestamp_ms=33.0, landmarks=[]),
    ]

    summary = summarize_clip_quality(frames)

    assert summary.total_frames == 2
    assert summary.pose_visibility_ratio == 0.5
    assert summary.full_body_visibility_ratio == 0.5
    assert summary.dominant_orientation in {"angle_readable", "unreadable"}


def _full_body_frame(frame_index: int, timestamp_ms: float) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        landmarks=[
            Landmark("nose", 0.5, 0.1, 0.0, 0.95),
            Landmark("left_shoulder", 0.42, 0.25, 0.0, 0.95),
            Landmark("right_shoulder", 0.58, 0.25, 0.0, 0.95),
            Landmark("left_elbow", 0.38, 0.36, 0.0, 0.95),
            Landmark("right_elbow", 0.62, 0.36, 0.0, 0.95),
            Landmark("left_wrist", 0.36, 0.42, 0.0, 0.95),
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
