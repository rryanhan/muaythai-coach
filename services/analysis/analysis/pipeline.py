import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.jab import JabMetrics, Stance, analyze_jab_landmarks
from analysis.pose import MediaPipePoseEstimator, PoseFrame, pose_frames_to_json
from analysis.video import normalize_video, probe_video, write_pose_overlay


@dataclass(frozen=True)
class AnalysisPaths:
    # The pipeline needs to know two things:
    # where the source video is, and where all generated artifacts should go.
    input_video: Path
    output_dir: Path


@dataclass(frozen=True)
class JabAnalysisResult:
    # This is the small summary returned to callers after the full pipeline runs.
    # The detailed data still lives in result.json and landmarks.json.
    detected_reps: int
    rear_hand_drops: int
    hand_dip_telegraphs: int
    average_return_time_ms: float | None
    confidence: str
    output_dir: Path
    landmarks_path: Path
    result_path: Path
    overlay_path: Path | None


def analyze_jab_video(
    paths: AnalysisPaths,
    stance: Stance = "orthodox",
    generate_overlay: bool = True,
    normalize_fps: int | None = None,
    normalize_width: int = 720,
) -> JabAnalysisResult:
    # Main orchestration function for the first prototype:
    # video file -> normalized video -> landmarks -> jab metrics -> debug overlay -> result JSON.
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    # These are the first-debuggable artifacts for every run. If a metric looks wrong,
    # inspect landmarks.json and overlay.mp4 before changing thresholds.
    normalized_video = paths.output_dir / "normalized.mp4"
    landmarks_path = paths.output_dir / "landmarks.json"
    result_path = paths.output_dir / "result.json"
    overlay_path = paths.output_dir / "overlay.mp4"
    metadata_path = paths.output_dir / "metadata.json"

    metadata = probe_video(paths.input_video)
    _write_json(metadata_path, metadata)

    # Normalize before pose estimation so phone videos with different frame rates,
    # rotations, encodings, or resolutions enter the analysis in a predictable shape.
    normalize_video(paths.input_video, normalized_video, fps=normalize_fps, width=normalize_width)

    # MediaPipe gives us generic body landmarks. The jab module is where we interpret
    # those landmarks as Muay Thai-specific events like extension, return, and guard drop.
    estimator = MediaPipePoseEstimator()
    frames = estimator.estimate_video(normalized_video)
    _write_json(landmarks_path, pose_frames_to_json(frames))

    metrics = analyze_jab_landmarks(frames, stance=stance)

    # Overlay video is a developer sanity check, but it is expensive. The CLI keeps
    # it on by default; the web upload path can skip it for faster feedback.
    generated_overlay_path = overlay_path if generate_overlay else None
    if generated_overlay_path is not None:
        write_pose_overlay(normalized_video, generated_overlay_path, frames)
    diagnostics = _visibility_diagnostics(frames)
    _write_json(
        result_path,
        _result_payload(paths.input_video, stance, metrics, generated_overlay_path, diagnostics),
    )

    # Return a compact object so the CLI/API can print or send a summary without
    # re-opening the JSON files it just wrote.
    return JabAnalysisResult(
        detected_reps=metrics.detected_reps,
        rear_hand_drops=metrics.rear_hand_drops,
        hand_dip_telegraphs=metrics.hand_dip_telegraphs,
        average_return_time_ms=metrics.average_return_time_ms,
        confidence=metrics.confidence,
        output_dir=paths.output_dir,
        landmarks_path=landmarks_path,
        result_path=result_path,
        overlay_path=generated_overlay_path,
    )


def default_output_dir(input_video: Path, output_root: Path) -> Path:
    # Example: data/videos/good_jab.mp4 -> data/outputs/good_jab/
    return output_root / input_video.stem


def _result_payload(
    input_video: Path,
    stance: Stance,
    metrics: JabMetrics,
    overlay_path: Path | None,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    # This is the user/developer-facing JSON shape. It should stay boring and explicit
    # so it can later become an API response with minimal translation.
    return {
        "test_type": "jab",
        "stance": stance,
        "input_video": str(input_video),
        "overlay_video": str(overlay_path) if overlay_path is not None else None,
        "metrics": metrics.to_json(),
        "diagnostics": diagnostics,
        "notes": [
            (
                "First-pass rule-based prototype. Thresholds should be tuned against "
                "real sample videos."
            ),
            "Average return time is measured from detected max extension to guard recovery.",
        ],
    }


def _visibility_diagnostics(
    frames: list[PoseFrame],
    min_confidence: float = 0.35,
) -> dict[str, Any]:
    landmark_names = [
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
    ]
    total_frames = len(frames)
    frames_with_any_pose = sum(1 for frame in frames if frame.landmarks)
    landmarks: dict[str, Any] = {}

    for name in landmark_names:
        visible_confidences: list[float] = []
        for frame in frames:
            landmark = frame.landmark_map().get(name)
            confidence = landmark.confidence if landmark else None
            if confidence is not None and confidence >= min_confidence:
                visible_confidences.append(confidence)

        visible_frames = len(visible_confidences)
        landmarks[name] = {
            "visible_frames": visible_frames,
            "visibility_ratio": _ratio(visible_frames, total_frames),
            "average_confidence_when_visible": (
                round(sum(visible_confidences) / visible_frames, 3)
                if visible_frames
                else None
            ),
        }

    return {
        "total_frames": total_frames,
        "frames_with_any_pose": frames_with_any_pose,
        "pose_visibility_ratio": _ratio(frames_with_any_pose, total_frames),
        "min_confidence": min_confidence,
        "landmarks": landmarks,
    }


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 3)


def _write_json(path: Path, payload: Any) -> None:
    # Centralized JSON writing keeps every output formatted the same way.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
