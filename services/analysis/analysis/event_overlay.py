import json
import subprocess
from pathlib import Path
from typing import Any, cast

import cv2

from analysis.pose import Landmark, PoseFrame

POSE_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]


def write_event_overlay(
    *,
    normalized_video: Path,
    landmarks_path: Path,
    events_path: Path,
    output_video: Path,
) -> Path:
    frames = _read_pose_frames(landmarks_path)
    strikes = _read_straight_strikes(events_path)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    raw_output = output_video.with_name(f"{output_video.stem}.raw.mp4")

    capture = cv2.VideoCapture(str(normalized_video))
    if not capture.isOpened():
        raise ValueError(f"Could not open normalized video: {normalized_video}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(
        str(raw_output),
        cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore[attr-defined]
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise ValueError(f"Could not create event overlay video: {raw_output}")

    frame_by_index = {frame.frame_index: frame for frame in frames}
    frame_index = 0
    while True:
        ok, image = capture.read()
        if not ok:
            break

        timestamp_ms = (frame_index / fps) * 1000.0
        pose_frame = frame_by_index.get(frame_index)
        if pose_frame is not None:
            _draw_landmarks(image, pose_frame, width, height)
        _draw_active_strikes(image, strikes, timestamp_ms)
        _draw_timestamp(image, timestamp_ms)

        writer.write(image)
        frame_index += 1

    capture.release()
    writer.release()
    _transcode_to_playable_mp4(raw_output, output_video)
    raw_output.unlink(missing_ok=True)
    return output_video


def _draw_landmarks(image: Any, frame: PoseFrame, width: int, height: int) -> None:
    landmarks = frame.landmark_map()
    for start_name, end_name in POSE_CONNECTIONS:
        start = _visible(landmarks.get(start_name))
        end = _visible(landmarks.get(end_name))
        if start is None or end is None:
            continue
        cv2.line(
            image,
            (int(start.x * width), int(start.y * height)),
            (int(end.x * width), int(end.y * height)),
            (255, 210, 90),
            2,
        )

    for landmark in frame.landmarks:
        if _visible(landmark) is None:
            continue
        color = (70, 120, 255) if landmark.name.startswith("left") else (60, 220, 255)
        cv2.circle(image, (int(landmark.x * width), int(landmark.y * height)), 3, color, -1)


def _draw_active_strikes(
    image: Any,
    strikes: list[dict[str, Any]],
    timestamp_ms: float,
) -> None:
    active = [
        strike
        for strike in strikes
        if float(strike["start_ms"]) <= timestamp_ms <= float(strike["end_ms"])
    ]
    if not active:
        return

    for index, strike in enumerate(active):
        strike_type = str(strike["strike_type"]).upper()
        confidence = str(strike["confidence"]).upper()
        label = f"{strike_type} · {confidence}"
        color = (64, 88, 255) if strike_type == "JAB" else (255, 170, 64)
        x = 24
        y = 42 + index * 38
        cv2.rectangle(image, (x - 8, y - 28), (x + 210, y + 8), (20, 24, 30), -1)
        cv2.rectangle(image, (x - 8, y - 28), (x + 210, y + 8), color, 2)
        cv2.putText(
            image,
            label,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            cv2.LINE_AA,
        )


def _draw_timestamp(image: Any, timestamp_ms: float) -> None:
    label = f"{timestamp_ms / 1000.0:05.2f}s"
    cv2.putText(
        image,
        label,
        (24, image.shape[0] - 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (235, 235, 235),
        2,
        cv2.LINE_AA,
    )


def _read_straight_strikes(path: Path) -> list[dict[str, Any]]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    straight_strikes = cast(dict[str, Any], payload["straight_strikes"])
    return cast(list[dict[str, Any]], straight_strikes["strikes"])


def _read_pose_frames(path: Path) -> list[PoseFrame]:
    raw_frames = cast(list[dict[str, Any]], json.loads(path.read_text(encoding="utf-8")))
    frames: list[PoseFrame] = []
    for raw_frame in raw_frames:
        raw_landmarks = cast(list[dict[str, Any]], raw_frame.get("landmarks", []))
        landmarks = [
            Landmark(
                name=str(raw_landmark["name"]),
                x=float(raw_landmark["x"]),
                y=float(raw_landmark["y"]),
                z=(
                    float(raw_landmark["z"])
                    if raw_landmark.get("z") is not None
                    else None
                ),
                confidence=(
                    float(raw_landmark["confidence"])
                    if raw_landmark.get("confidence") is not None
                    else None
                ),
            )
            for raw_landmark in raw_landmarks
        ]
        frames.append(
            PoseFrame(
                frame_index=int(raw_frame["frame_index"]),
                timestamp_ms=float(raw_frame["timestamp_ms"]),
                landmarks=landmarks,
            )
        )
    return frames


def _visible(landmark: Landmark | None, min_confidence: float = 0.35) -> Landmark | None:
    if landmark is None:
        return None
    if (landmark.confidence or 0.0) < min_confidence:
        return None
    return landmark


def _transcode_to_playable_mp4(raw_video: Path, output_video: Path) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(raw_video),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        str(output_video),
    ]
    subprocess.run(command, check=True)
