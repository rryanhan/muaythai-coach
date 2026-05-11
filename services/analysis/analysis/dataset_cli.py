import argparse
from pathlib import Path

from analysis.dataset import run_dataset_manifest
from analysis.video import ensure_ffmpeg_available


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run calibration and quality diagnostics for a labeled video dataset."
    )
    parser.add_argument("manifest", type=Path, help="Path to the dataset manifest JSON.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("../../data/outputs"),
        help="Directory where dataset outputs are written.",
    )
    parser.add_argument(
        "--normalize-fps",
        type=int,
        default=30,
        help="Frame rate used for faster offline review. Use 0 to preserve source FPS.",
    )
    parser.add_argument(
        "--normalize-width",
        type=int,
        default=540,
        help="Video width used before pose estimation.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Recompute landmarks even if a clip already has cached output.",
    )
    parser.add_argument(
        "--clip",
        action="append",
        default=None,
        help="Process one named clip plus required calibration clips. Can be repeated.",
    )
    args = parser.parse_args()

    if not ensure_ffmpeg_available():
        raise SystemExit("FFmpeg is not available on PATH.")

    normalize_fps = None if args.normalize_fps == 0 else args.normalize_fps
    result = run_dataset_manifest(
        manifest_path=args.manifest.expanduser().resolve(),
        output_root=args.output_root.expanduser().resolve(),
        normalize_fps=normalize_fps,
        normalize_width=args.normalize_width,
        reuse_existing=not args.no_cache,
        clip_names=set(args.clip) if args.clip else None,
    )

    print("Dataset analysis complete")
    print(f"Dataset: {result.dataset}")
    print(f"Output dir: {result.output_dir}")
    print(f"Calibration profile: {result.calibration_profile_path}")
    print(f"Summary JSON: {result.summary_json_path}")
    print(f"Summary Markdown: {result.summary_markdown_path}")


if __name__ == "__main__":
    main()
