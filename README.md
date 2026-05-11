# Muay Thai AI Form Coach

Mobile-web MVP for constrained Muay Thai striking tests: jab, cross, and jab-cross. The first goal is to prove that phone video plus pose estimation can reliably detect beginner-relevant issues like guard drops, return-to-guard time, elbow flare, telegraphing, punch path, stance stability, and estimated punch speed.

## Current Focus

The repo is set up for technical validation before product polish:

1. Capture or upload short test videos.
2. Run server-side pose estimation.
3. Generate landmark data and debug overlays.
4. Detect simple jab/cross metrics.
5. Extract issue clips that show visible evidence.

## Stack

- Frontend: Next.js, React, TypeScript, mobile-first web UI
- Backend/API: FastAPI, Python
- Pose analysis: MediaPipe Pose Landmarker or BlazePose first
- Video processing: OpenCV for frame processing, FFmpeg for normalization and clip extraction
- Package management: pnpm for web, Python virtualenv/pip for analysis service

## Repo Layout

```txt
apps/
  web/                  Mobile web app
services/
  analysis/             FastAPI service and pose-analysis pipeline
docs/
  architecture.md       Technical architecture notes
data/
  videos/               Local sample videos, ignored by git
  outputs/              Generated overlays/clips, ignored by git
  tmp/                  Temporary processing files, ignored by git
```

## Local Setup

Web app:

```bash
pnpm install
pnpm dev:web
```

Analysis service:

```bash
cd services/analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

FFmpeg is required for video normalization and issue clips:

```bash
brew install ffmpeg
```

## First Prototype Target

Build the smallest possible proof:

- Upload one jab-test video.
- Run pose estimation.
- Save landmarks.
- Produce a skeleton overlay.
- Detect lead wrist leaving and returning to guard.
- Detect rear hand dropping during jab.
- Extract one issue clip.

