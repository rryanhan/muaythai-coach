import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from analysis.calibration import CalibrationProfile, Stance, build_calibration_profile
from analysis.events import detect_motion_events
from analysis.gating import FrameGate, GateSummary, build_frame_gates, summarize_frame_gates
from analysis.pose import Landmark, MediaPipePoseEstimator, PoseFrame, pose_frames_to_json
from analysis.quality import ClipQualitySummary, summarize_clip_quality
from analysis.strikes import analyze_straight_strikes
from analysis.video import normalize_video, probe_video


@dataclass(frozen=True)
class DatasetClip:
    filename: str
    category: str
    primary_action: str
    stance: Stance
    expected_reps: int | None
    expected_issues: list[str]
    use_for: list[str]
    notes: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessedClip:
    clip: DatasetClip
    source_path: Path
    output_dir: Path
    frames: list[PoseFrame]
    quality: ClipQualitySummary
    gates: list[FrameGate]
    gate_summary: GateSummary


@dataclass(frozen=True)
class DatasetRunResult:
    dataset: str
    output_dir: Path
    calibration_profile_path: Path
    summary_json_path: Path
    summary_markdown_path: Path


def load_manifest(manifest_path: Path) -> tuple[str, Stance, list[DatasetClip]]:
    payload = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    dataset = str(payload["dataset"])
    default_stance = cast(Stance, payload.get("stance", "orthodox"))
    raw_clips = cast(list[dict[str, Any]], payload["clips"])
    clips = [
        DatasetClip(
            filename=str(raw_clip["filename"]),
            category=str(raw_clip["category"]),
            primary_action=str(raw_clip["primary_action"]),
            stance=cast(Stance, raw_clip.get("stance", default_stance)),
            expected_reps=cast(int | None, raw_clip.get("expected_reps")),
            expected_issues=[str(issue) for issue in raw_clip.get("expected_issues", [])],
            use_for=[str(use) for use in raw_clip.get("use_for", [])],
            notes=str(raw_clip.get("notes", "")),
        )
        for raw_clip in raw_clips
    ]
    return dataset, default_stance, clips


def run_dataset_manifest(
    manifest_path: Path,
    output_root: Path,
    *,
    normalize_fps: int | None = 30,
    normalize_width: int = 540,
    reuse_existing: bool = True,
    clip_names: set[str] | None = None,
) -> DatasetRunResult:
    dataset, stance, clips = load_manifest(manifest_path)
    dataset_dir = output_root / dataset
    dataset_dir.mkdir(parents=True, exist_ok=True)
    source_root = manifest_path.parent

    selected_clips = [
        clip for clip in clips if clip_names is None or clip.filename in clip_names
    ]
    if clip_names is not None:
        selected_clips = _include_required_calibration(clips, selected_clips)

    estimator = MediaPipePoseEstimator()
    processed_clips = [
        _process_clip(
            clip=clip,
            source_root=source_root,
            dataset_dir=dataset_dir,
            estimator=estimator,
            normalize_fps=normalize_fps,
            normalize_width=normalize_width,
            reuse_existing=reuse_existing,
        )
        for clip in selected_clips
    ]

    calibration_profile = _build_profile(dataset, stance, processed_clips)
    calibration_profile_path = dataset_dir / "calibration_profile.json"
    _write_json(calibration_profile_path, calibration_profile.to_json())

    clip_summaries = [
        _clip_summary_payload(processed_clip, calibration_profile)
        for processed_clip in processed_clips
    ]
    summary_payload = {
        "dataset": dataset,
        "stance": stance,
        "manifest": str(manifest_path),
        "calibration_profile": str(calibration_profile_path),
        "clip_count": len(clip_summaries),
        "clips": clip_summaries,
    }
    summary_json_path = dataset_dir / "dataset_summary.json"
    summary_markdown_path = dataset_dir / "dataset_summary.md"
    _write_json(summary_json_path, summary_payload)
    summary_markdown_path.write_text(
        _markdown_report(summary_payload),
        encoding="utf-8",
    )

    return DatasetRunResult(
        dataset=dataset,
        output_dir=dataset_dir,
        calibration_profile_path=calibration_profile_path,
        summary_json_path=summary_json_path,
        summary_markdown_path=summary_markdown_path,
    )


def _include_required_calibration(
    clips: list[DatasetClip],
    selected_clips: list[DatasetClip],
) -> list[DatasetClip]:
    selected_names = {clip.filename for clip in selected_clips}
    required_actions = {
        "full_body_visibility",
        "lead_reach",
        "rear_reach",
        "movement_baseline",
    }
    calibration_clips = [
        clip
        for clip in clips
        if clip.category == "calibration" and clip.primary_action in required_actions
    ]
    calibration_names = {clip.filename for clip in calibration_clips}
    combined = calibration_clips + [
        clip for clip in selected_clips if clip.filename not in calibration_names
    ]
    return [
        clip
        for clip in combined
        if clip.filename in selected_names or clip.category == "calibration"
    ]


def _process_clip(
    *,
    clip: DatasetClip,
    source_root: Path,
    dataset_dir: Path,
    estimator: MediaPipePoseEstimator,
    normalize_fps: int | None,
    normalize_width: int,
    reuse_existing: bool,
) -> ProcessedClip:
    source_path = source_root / clip.filename
    if not source_path.exists():
        raise FileNotFoundError(f"Manifest clip does not exist: {source_path}")

    output_dir = dataset_dir / Path(clip.filename).stem
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "metadata.json"
    normalized_path = output_dir / "normalized.mp4"
    landmarks_path = output_dir / "landmarks.json"
    quality_path = output_dir / "quality.json"
    gating_path = output_dir / "gating.json"

    if reuse_existing and landmarks_path.exists():
        frames = _read_pose_frames(landmarks_path)
    else:
        metadata = probe_video(source_path)
        _write_json(metadata_path, metadata)
        normalize_video(
            source_path,
            normalized_path,
            fps=normalize_fps,
            width=normalize_width,
        )
        frames = estimator.estimate_video(normalized_path)
        _write_json(landmarks_path, pose_frames_to_json(frames))

    quality = summarize_clip_quality(frames)
    gates = build_frame_gates(frames, stance=clip.stance)
    gate_summary = summarize_frame_gates(gates)
    _write_json(quality_path, quality.to_json())
    _write_json(
        gating_path,
        {
            "summary": gate_summary.to_json(),
            "frames": [gate.to_json() for gate in gates],
        },
    )

    return ProcessedClip(
        clip=clip,
        source_path=source_path,
        output_dir=output_dir,
        frames=frames,
        quality=quality,
        gates=gates,
        gate_summary=gate_summary,
    )


def _build_profile(
    dataset: str,
    stance: Stance,
    processed_clips: list[ProcessedClip],
) -> CalibrationProfile:
    by_action = {
        processed.clip.primary_action: processed.frames
        for processed in processed_clips
        if processed.clip.category == "calibration"
    }
    source_files = [
        processed.clip.filename
        for processed in processed_clips
        if processed.clip.category == "calibration"
    ]
    return build_calibration_profile(
        dataset=dataset,
        stance=stance,
        source_files=source_files,
        full_body_frames=by_action.get("full_body_visibility", []),
        lead_reach_frames=by_action.get("lead_reach", []),
        rear_reach_frames=by_action.get("rear_reach", []),
        movement_baseline_frames=by_action.get("movement_baseline", []),
    )


def _clip_summary_payload(
    processed_clip: ProcessedClip,
    calibration_profile: CalibrationProfile,
) -> dict[str, Any]:
    clip = processed_clip.clip
    quality = processed_clip.quality
    events = detect_motion_events(
        processed_clip.frames,
        processed_clip.gates,
        calibration_profile,
        clip.stance,
    )
    straight_strikes = analyze_straight_strikes(events)
    review = _review_guidance(clip, quality, calibration_profile)
    straight_strike_review = _straight_strike_review(clip, straight_strikes.to_json())
    _write_json(
        processed_clip.output_dir / "events.json",
        {
            "gating": processed_clip.gate_summary.to_json(),
            "motion_events": events.to_json(),
            "straight_strikes": straight_strikes.to_json(),
            "straight_strike_review": straight_strike_review,
        },
    )
    return {
        "clip": clip.to_json(),
        "source_path": str(processed_clip.source_path),
        "output_dir": str(processed_clip.output_dir),
        "quality": quality.to_json(),
        "gating": processed_clip.gate_summary.to_json(),
        "motion_events": events.to_json(),
        "straight_strikes": straight_strikes.to_json(),
        "calibration_fit": review,
        "straight_strike_review": straight_strike_review,
    }


def _review_guidance(
    clip: DatasetClip,
    quality: ClipQualitySummary,
    calibration_profile: CalibrationProfile,
) -> dict[str, Any]:
    warnings: list[str] = []
    required_hand_landmarks = _required_hand_landmarks(clip)
    needs_feet = (
        clip.category == "movement"
        or clip.primary_action in {"footwork", "step_left", "step_right"}
        or "footwork_detection" in clip.use_for
    )

    if quality.pose_visibility_ratio < 0.7:
        warnings.append("Pose is missing for a large part of the clip.")
    if quality.torso_visibility_ratio < 0.7:
        warnings.append(
            "Torso visibility is weak, so orientation and stance checks may be unstable."
        )
    for landmark_name in required_hand_landmarks:
        visibility_ratio = quality.landmark_visibility_ratios.get(landmark_name, 0.0)
        if visibility_ratio < 0.65:
            warnings.append(f"{landmark_name} visibility is weak for this clip.")
    if needs_feet and quality.feet_visibility_ratio < 0.65:
        warnings.append("Foot visibility is weak for a movement/footwork clip.")
    if quality.dominant_orientation in {"partially_occluded", "unreadable"}:
        warnings.append("Dominant orientation is low-trust.")

    baseline_ratio = calibration_profile.orientation.get("average_torso_width_to_height")
    clip_ratio = quality.average_torso_width_to_height
    torso_width_ratio = (
        round(clip_ratio / baseline_ratio, 3)
        if isinstance(baseline_ratio, float)
        and baseline_ratio > 0
        and clip_ratio is not None
        else None
    )

    return {
        "usable_for_rule_tuning": not warnings or clip.category in {"angle", "mistake"},
        "manual_review_priority": _manual_review_priority(clip, warnings),
        "warnings": warnings,
        "dominant_orientation": quality.dominant_orientation,
        "baseline_orientation": calibration_profile.orientation.get("dominant_orientation"),
        "torso_width_ratio_vs_calibration": torso_width_ratio,
        "required_hand_landmarks": {
            landmark_name: quality.landmark_visibility_ratios.get(landmark_name, 0.0)
            for landmark_name in required_hand_landmarks
        },
        "expected_reps_are_approximate": clip.expected_reps is not None,
    }


def _required_hand_landmarks(clip: DatasetClip) -> list[str]:
    lead_wrist = _lead_name(clip.stance, "wrist")
    rear_wrist = _rear_name(clip.stance, "wrist")
    lead_elbow = _lead_name(clip.stance, "elbow")
    rear_elbow = _rear_name(clip.stance, "elbow")

    if clip.primary_action in {"lead_reach", "lead_hook", "lead_uppercut"}:
        return [lead_wrist, lead_elbow]
    if clip.primary_action in {"rear_reach", "rear_hook", "rear_uppercut"}:
        return [rear_wrist, rear_elbow]
    if clip.primary_action == "jab":
        return [lead_wrist, lead_elbow, rear_wrist]
    if clip.primary_action == "cross":
        return [rear_wrist, rear_elbow, lead_wrist]
    if clip.primary_action == "jab_cross":
        return [lead_wrist, lead_elbow, rear_wrist, rear_elbow]
    return []


def _straight_strike_review(
    clip: DatasetClip,
    straight_strikes: dict[str, Any],
) -> dict[str, Any]:
    expected_types = _expected_straight_strike_types(clip.primary_action)
    counts = cast(dict[str, int], straight_strikes["high_or_medium_counts"])
    warnings: list[str] = []

    for strike_type in expected_types:
        detected_count = counts.get(strike_type, 0)
        if detected_count == 0:
            warnings.append(f"expected_{strike_type}_not_detected")
        if clip.expected_reps is not None and abs(detected_count - clip.expected_reps) > 3:
            warnings.append(
                f"{strike_type}_count_far_from_expected_{detected_count}_vs_{clip.expected_reps}"
            )

    unexpected_types = [
        strike_type for strike_type in ["jab", "cross"] if strike_type not in expected_types
    ]
    for strike_type in unexpected_types:
        if expected_types and counts.get(strike_type, 0) > 2:
            warnings.append(f"unexpected_{strike_type}_candidates")

    straight_count = counts.get("jab", 0) + counts.get("cross", 0)
    if clip.primary_action in {
        "lead_hook",
        "rear_hook",
        "lead_uppercut",
        "rear_uppercut",
    }:
        if straight_count > 2:
            warnings.append("non_straight_clip_has_many_straight_candidates")
    if clip.category == "movement" or clip.primary_action in {
        "footwork",
        "step_left",
        "step_right",
        "pivot_clockwise",
        "pivot_counter_clockwise",
    }:
        if straight_count > 2:
            warnings.append("movement_clip_has_many_straight_candidates")

    return {
        "expected_straight_strikes": expected_types,
        "detected_high_or_medium": counts,
        "warnings": warnings,
        "manual_review_priority": "high" if warnings else "normal",
    }


def _expected_straight_strike_types(primary_action: str) -> list[str]:
    if primary_action == "jab":
        return ["jab"]
    if primary_action == "cross":
        return ["cross"]
    if primary_action == "jab_cross":
        return ["jab", "cross"]
    return []


def _lead_name(stance: Stance, landmark: str) -> str:
    side = "left" if stance == "orthodox" else "right"
    return f"{side}_{landmark}"


def _rear_name(stance: Stance, landmark: str) -> str:
    side = "right" if stance == "orthodox" else "left"
    return f"{side}_{landmark}"


def _manual_review_priority(clip: DatasetClip, warnings: list[str]) -> str:
    if warnings:
        return "high"
    if clip.category in {"mistake", "angle", "freestyle"}:
        return "medium"
    return "normal"


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _markdown_report(summary_payload: dict[str, Any]) -> str:
    clips = cast(list[dict[str, Any]], summary_payload["clips"])
    lines = [
        f"# Dataset Summary: {summary_payload['dataset']}",
        "",
        f"- Stance: `{summary_payload['stance']}`",
        f"- Clips processed: `{summary_payload['clip_count']}`",
        f"- Calibration profile: `{summary_payload['calibration_profile']}`",
        "",
        (
            "| Clip | Category | Action | Orientation | Lead% | Rear% | Move% | "
            "Jab | Cross | Review | Warnings |"
        ),
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in clips:
        clip = cast(dict[str, Any], item["clip"])
        quality = cast(dict[str, Any], item["quality"])
        gating = cast(dict[str, Any], item["gating"])
        fit = cast(dict[str, Any], item["calibration_fit"])
        strike_review = cast(dict[str, Any], item["straight_strike_review"])
        strike_counts = cast(dict[str, int], strike_review["detected_high_or_medium"])
        warnings = [
            *cast(list[str], fit["warnings"]),
            *cast(list[str], strike_review["warnings"]),
        ]
        lines.append(
            " | ".join(
                [
                    _escape_markdown_table(str(clip["filename"])),
                    _escape_markdown_table(str(clip["category"])),
                    _escape_markdown_table(str(clip["primary_action"])),
                    _escape_markdown_table(str(quality["dominant_orientation"])),
                    str(gating["lead_hand_available_ratio"]),
                    str(gating["rear_hand_available_ratio"]),
                    str(gating["movement_available_ratio"]),
                    str(strike_counts.get("jab", 0)),
                    str(strike_counts.get("cross", 0)),
                    _escape_markdown_table(str(fit["manual_review_priority"])),
                    _escape_markdown_table("; ".join(warnings) if warnings else "none"),
                ]
            ).join(["| ", " |"])
        )
    lines.append("")
    return "\n".join(lines)


def _escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|")
