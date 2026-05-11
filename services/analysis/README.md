# Analysis Service

FastAPI service for server-side video processing, pose estimation, metrics, and issue clip generation.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## First Technical Slice

The first useful implementation should support:

1. Upload a jab-test video.
2. Normalize the video with FFmpeg.
3. Run pose estimation on frames.
4. Save landmark time series.
5. Detect jab reps.
6. Detect rear hand drop.
7. Calculate return-to-guard time.
8. Extract one issue clip.

## Local Media

Put sample videos in:

```txt
data/videos/
```

Generated overlays, clips, and landmarks should go in:

```txt
data/outputs/
```

Both locations are ignored by git except for `.gitkeep` files.

