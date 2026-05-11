# Muay Thai AI Form Coach

Mobile-web MVP for constrained Muay Thai striking tests: jab, cross, and jab-cross. The first goal is to prove that phone video plus pose estimation can reliably detect beginner-relevant issues like guard drops, return-to-guard time, elbow flare, telegraphing, punch path, stance stability, and estimated punch speed.


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



