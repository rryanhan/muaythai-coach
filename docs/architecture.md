# Architecture

## Product Shape

The MVP has two main surfaces:

- Mobile web frontend for guided recording and result review
- Server-side analysis service for video processing, pose estimation, metrics, and issue clips

The first milestone should validate the analysis pipeline before investing heavily in UI, accounts, or polished onboarding.

## High-Level Flow

1. User records or uploads a constrained test video.
2. Frontend sends video to the analysis API.
3. API stores the file temporarily.
4. FFmpeg normalizes the video format, rotation, frame rate, and resolution.
5. OpenCV reads frames.
6. Pose model extracts landmarks for each frame.
7. Landmarks are smoothed.
8. Rep detection segments strikes.
9. Metrics engine calculates issues and confidence labels.
10. FFmpeg extracts short issue clips.
11. API returns structured results.
12. Original video is deleted after processing.

## Analysis Service Responsibilities

- Validate uploaded video
- Normalize media with FFmpeg
- Run pose estimation
- Save landmark time series
- Detect reps
- Calculate metrics
- Assign confidence labels
- Generate temporary clips
- Return results JSON
- Delete original uploads after analysis

## Frontend Responsibilities

- Mobile-first capture flow
- Stance selection
- Setup and calibration guidance
- Upload progress
- Analysis status
- Staged result display
- Temporary issue clip playback
- Drill recommendation display

## Early Technical Bet

The key risk is not UI. The key risk is whether a normal phone video can produce stable enough landmarks to detect meaningful striking issues.

Validate these first:

- Pose detection success rate
- Wrist/elbow/shoulder stability
- Rep segmentation accuracy
- Rear-hand-drop detection
- Return-to-guard timing
- Clip extraction around detected issues

