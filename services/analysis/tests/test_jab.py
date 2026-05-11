from analysis.jab import analyze_jab_landmarks
from analysis.pose import Landmark, PoseFrame


def test_analyze_jab_landmarks_detects_reps_and_rear_hand_drop() -> None:
    frames: list[PoseFrame] = []
    timestamp_ms = 0.0
    for rep in range(3):
        for extension, rear_drop in [
            (0.08, False),
            (0.16, False),
            (0.28, rep == 1),
            (0.42, rep == 1),
            (0.24, rep == 1),
            (0.09, False),
        ]:
            frames.append(_frame(len(frames), timestamp_ms, extension, rear_drop))
            timestamp_ms += 50.0
        for _ in range(2):
            frames.append(_frame(len(frames), timestamp_ms, 0.08, False))
            timestamp_ms += 50.0

    metrics = analyze_jab_landmarks(frames, stance="orthodox")

    assert metrics.detected_reps == 3
    assert metrics.rear_hand_drops == 1
    assert metrics.hand_dip_telegraphs == 0
    assert metrics.average_extension_time_ms == 50.0
    assert metrics.average_extension_speed_normalized == 0.533
    assert metrics.average_peak_extension_velocity_normalized == 2.267
    assert metrics.average_return_time_ms == 100.0
    assert metrics.confidence == "Medium"


def test_analyze_jab_landmarks_returns_low_confidence_when_landmarks_missing() -> None:
    frames = [
        PoseFrame(frame_index=index, timestamp_ms=index * 33.3, landmarks=[])
        for index in range(20)
    ]

    metrics = analyze_jab_landmarks(frames, stance="orthodox")

    assert metrics.detected_reps == 0
    assert metrics.confidence == "Low"


def test_analyze_jab_landmarks_flags_lead_hand_dip_before_jab() -> None:
    frames: list[PoseFrame] = []
    timestamp_ms = 0.0

    # The first second is quiet guard, then the lead wrist dips before each jab.
    for _ in range(20):
        frames.append(_frame(len(frames), timestamp_ms, 0.08, False))
        timestamp_ms += 50.0

    for _ in range(3):
        for extension, lead_dip in [
            (0.08, 0.0),
            (0.08, 0.16),
            (0.16, 0.16),
            (0.28, 0.0),
            (0.42, 0.0),
            (0.24, 0.0),
            (0.09, 0.0),
        ]:
            frames.append(_frame(len(frames), timestamp_ms, extension, False, lead_dip))
            timestamp_ms += 50.0
        for _ in range(8):
            frames.append(_frame(len(frames), timestamp_ms, 0.08, False))
            timestamp_ms += 50.0

    metrics = analyze_jab_landmarks(frames, stance="orthodox")

    assert metrics.detected_reps == 3
    assert metrics.hand_dip_telegraphs == 3


def _frame(
    frame_index: int,
    timestamp_ms: float,
    lead_extension: float,
    rear_drop: bool,
    lead_dip: float = 0.0,
) -> PoseFrame:
    left_shoulder_x = 0.4
    right_shoulder_y = 0.3
    right_wrist_y = 0.42 if rear_drop else 0.34
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        landmarks=[
            Landmark("left_shoulder", left_shoulder_x, 0.3, 0.0, 0.95),
            Landmark("right_shoulder", 0.6, right_shoulder_y, 0.0, 0.95),
            Landmark("left_wrist", left_shoulder_x + lead_extension, 0.32 + lead_dip, 0.0, 0.95),
            Landmark("right_wrist", 0.58, right_wrist_y, 0.0, 0.95),
        ],
    )
