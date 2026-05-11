import argparse
from pathlib import Path

from analysis.event_overlay import write_event_overlay
from analysis.video import ensure_ffmpeg_available


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a debug video with pose skeleton and jab/cross candidate labels."
    )
    parser.add_argument("clip_output_dir", type=Path, help="Per-clip output directory.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path. Defaults to labeled_overlay.mp4 in the clip output directory.",
    )
    args = parser.parse_args()

    if not ensure_ffmpeg_available():
        raise SystemExit("FFmpeg is not available on PATH.")

    clip_output_dir = args.clip_output_dir.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else clip_output_dir / "labeled_overlay.mp4"
    )
    result = write_event_overlay(
        normalized_video=clip_output_dir / "normalized.mp4",
        landmarks_path=clip_output_dir / "landmarks.json",
        events_path=clip_output_dir / "events.json",
        output_video=output,
    )
    print(f"Labeled overlay written: {result}")


if __name__ == "__main__":
    main()
