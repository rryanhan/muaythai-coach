import json
import subprocess
from pathlib import Path
from typing import Any, cast

import cv2

from analysis.pose import PoseFrame


def ensure_ffmpeg_available() -> bool:
    # subprocess.run lets Python call a normal terminal command.
    # Here we ask the system "does ffmpeg run?" before doing any video work.
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def probe_video(input_video: Path) -> dict[str, Any]:
    # ffprobe records original video facts like duration, codec, resolution, and frame rate.
    # This is useful when a clip fails or returns low confidence.
    # ffprobe inspects media; ffmpeg transforms media.
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_video),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return cast(dict[str, Any], json.loads(result.stdout))


def normalize_video(
    input_video: Path,
    output_video: Path,
    fps: int | None = None,
    width: int = 720,
) -> Path:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    # Normalize to a stable width and playable format before pose analysis.
    # When fps is None, preserve the source frame rate so 60/120fps timing tests keep
    # their extra temporal detail.
    # -y overwrites old output from a previous run.
    # -an removes audio because the analysis does not need it.
    # scale=720:-2 keeps the aspect ratio and chooses a valid even-numbered height.
    # yuv420p keeps output broadly playable instead of preserving phone HDR/10-bit formats.
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        _video_filter(width, fps),
        "-an",
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
    return output_video


def _video_filter(width: int, fps: int | None) -> str:
    filters = [f"scale={width}:-2"]
    if fps is not None:
        filters.append(f"fps={fps}")
    return ",".join(filters)


def write_pose_overlay(input_video: Path, output_video: Path, frames: list[PoseFrame]) -> None:
    # Draw the landmarks back onto the normalized video so we can visually debug
    # whether MediaPipe tracked the body parts we care about.
    capture = cv2.VideoCapture(str(input_video))
    if not capture.isOpened():
        raise ValueError(f"Could not open video for overlay: {input_video}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_video.parent.mkdir(parents=True, exist_ok=True)
    raw_overlay = output_video.with_name(f"{output_video.stem}.raw.mp4")

    # VideoWriter creates a new video file frame by frame. We read the original
    # normalized video, draw on each image, then write the modified frame here.
    # OpenCV writes reliable frames, but its MP4 codec is not always viewer-friendly,
    # so we transcode this temporary file to H.264 after drawing.
    writer = cv2.VideoWriter(
        str(raw_overlay),
        cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore[attr-defined]
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise ValueError(f"Could not create overlay video: {raw_overlay}")

    frame_by_index = {frame.frame_index: frame for frame in frames}
    frame_index = 0
    while True:
        # This mirrors pose.py: read one frame at a time until the video ends.
        ok, image = capture.read()
        if not ok:
            break

        pose_frame = frame_by_index.get(frame_index)
        if pose_frame:
            _draw_landmarks(image, pose_frame, width, height)
        writer.write(image)
        frame_index += 1

    capture.release()
    writer.release()
    _transcode_to_playable_mp4(raw_overlay, output_video)
    raw_overlay.unlink(missing_ok=True)


def _draw_landmarks(image: Any, frame: PoseFrame, width: int, height: int) -> None:
    landmark_map = frame.landmark_map()

    # This is a small custom skeleton. We only draw the body segments that matter
    # for early jab debugging instead of every MediaPipe landmark.
    connections = [
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
    ]

    for start_name, end_name in connections:
        start = landmark_map.get(start_name)
        end = landmark_map.get(end_name)
        if not start or not end:
            continue
        # Skip faint/uncertain landmarks in the overlay so the debug video does
        # not draw confident-looking lines on low-confidence detections.
        if (start.confidence or 0.0) < 0.35 or (end.confidence or 0.0) < 0.35:
            continue
        cv2.line(
            image,
            # MediaPipe stores x/y from 0..1, while OpenCV draws in pixel coordinates.
            (int(start.x * width), int(start.y * height)),
            (int(end.x * width), int(end.y * height)),
            (255, 208, 90),
            2,
        )

    for landmark in frame.landmarks:
        if (landmark.confidence or 0.0) < 0.35:
            continue
        # Left and right sides get different colors so we can quickly spot lead/rear hands.
        color = (63, 72, 229) if landmark.name.startswith("left") else (90, 207, 255)
        cv2.circle(image, (int(landmark.x * width), int(landmark.y * height)), 3, color, -1)


def extract_clip(
    input_video: Path,
    output_clip: Path,
    start_seconds: float,
    duration_seconds: float,
) -> None:
    output_clip.parent.mkdir(parents=True, exist_ok=True)
    # Later, detected issues will call this to create short evidence clips around a rep.
    # For example: a 2-second clip centered on the fourth jab where the rear hand dropped.
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(input_video),
        "-t",
        f"{duration_seconds:.3f}",
        "-c",
        "copy",
        str(output_clip),
    ]
    subprocess.run(command, check=True)


def _transcode_to_playable_mp4(input_video: Path, output_video: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    subprocess.run(command, check=True)
