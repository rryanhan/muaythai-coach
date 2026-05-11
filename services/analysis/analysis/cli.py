import argparse
from pathlib import Path

from analysis.pipeline import AnalysisPaths, analyze_jab_video, default_output_dir
from analysis.video import ensure_ffmpeg_available


def main() -> None:
    # This is the terminal-only entry point for the first prototype.
    # It runs one local video through the same pipeline the API will later call.
    parser = argparse.ArgumentParser(description="Run local Muay Thai jab analysis on a video.")
    parser.add_argument("video", type=Path, help="Path to a jab-test video.")
    parser.add_argument(
        "--stance",
        choices=["orthodox", "southpaw"],
        default="orthodox",
        help="Fighter stance. Orthodox is the default.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("../../data/outputs"),
        help="Directory where per-video analysis outputs are written.",
    )
    args = parser.parse_args()

    input_video = args.video.expanduser().resolve()
    if not input_video.exists():
        raise SystemExit(f"Video does not exist: {input_video}")
    if not ensure_ffmpeg_available():
        raise SystemExit("FFmpeg is not available on PATH.")

    # Each source video gets its own output folder so the generated files are easy to inspect.
    output_root = args.output_root.expanduser().resolve()
    output_dir = default_output_dir(input_video, output_root)
    result = analyze_jab_video(
        AnalysisPaths(input_video=input_video, output_dir=output_dir),
        stance=args.stance,
    )

    print("Jab analysis complete")
    print(f"Stance: {args.stance}")
    print(f"Detected reps: {result.detected_reps}")
    print(f"Rear hand drops: {result.rear_hand_drops}")
    print(f"Hand dip telegraphs: {result.hand_dip_telegraphs}")
    print(f"Average return time: {result.average_return_time_ms} ms")
    print(f"Confidence: {result.confidence}")
    print(f"Output dir: {result.output_dir}")
    print(f"Result JSON: {result.result_path}")
    print(f"Overlay video: {result.overlay_path}")


if __name__ == "__main__":
    main()
