# Muay Thai AI Form Coach PRD

## Overview

Build a mobile-web MVP for constrained Muay Thai striking tests. Users record jab, cross, and jab-cross tests in-app. The system analyzes video server-side, detects pose landmarks, calculates form metrics, extracts short issue clips, and returns immediate technical coaching feedback with curated drills.

The MVP should be designed as mobile web first, with architecture that can later become a native mobile app.

## Product Positioning

This is not a replacement for a coach. It is an objective video feedback tool for solo striking practice.

Positioning statement:

"Record a short striking test. Get measurable feedback on your guard, return speed, telegraphing, elbow flare, stance stability, and what to fix next."

## Target User

Primary V1 user:

- Beginner to intermediate Muay Thai student
- Trains at a gym and practices at home
- Wants useful feedback between classes
- Knows basic jab, cross, and jab-cross mechanics
- Needs direct, actionable form feedback

## V1 Goals

- Mobile-web guided assessment
- In-app recording
- Server-side analysis
- Jab, cross, and jab-cross tests
- Immediate post-recording results
- Pose-based detection of beginner-relevant issues
- Estimated punch speed with confidence labels
- Temporary issue clips showing detected problems
- Curated drill recommendations
- No persistent video storage

## Non-Goals

V1 will not include:

- Freestyle shadowboxing analysis
- Kicks, knees, elbows, clinch, bag work, pads, or sparring
- Real-time coaching
- Login or cloud profiles
- Coach dashboard
- Persistent video library
- Native iOS or Android app
- Overall form score
- Medical, rehab, or injury diagnosis

## Platform

V1 platform: mobile web.

Rationale:

- Users are more likely to record training on a phone than a laptop
- Mobile web avoids app store friction
- UX can still be app-like
- Native mobile can come later if the product proves useful

## Core User Journey

1. User opens mobile web app.
2. User starts guided striking assessment.
3. User selects orthodox or southpaw.
4. App shows camera setup instructions.
5. User completes setup/calibration.
6. User records jab test.
7. User records cross test.
8. User records jab-cross test.
9. Videos are uploaded for server-side analysis.
10. Server extracts pose, detects reps, calculates metrics, identifies issues, and creates issue clips.
11. User sees staged results: summary, metric breakdown, issue clips, and drills.
12. User can retake an individual test or restart the assessment.

## Camera Setup

Recommended setup:

- Phone on tripod, chair, shelf, or stable surface
- Full body visible from head to feet
- Camera around chest height
- Good lighting
- Minimal background clutter
- User far enough back that hands and feet stay in frame
- Front three-quarter view, about 30-60 degrees off center
- Ideal angle: about 45 degrees
- Lead side slightly closer to camera

Orthodox: left/lead side closer.

Southpaw: right/lead side closer.

Why 45 degrees:

- Balances front-facing guard visibility with side-facing punch mechanics
- Reduces depth ambiguity versus straight-on camera
- Reduces limb occlusion versus pure side view
- Helps detect guard, hand return, elbow flare, telegraphing, extension, overreach, and stance stability

## Calibration

Calibration is mandatory in V1 and should take less than 30 seconds.

Calibration flow:

1. Select stance.
2. Stand in fighting stance.
3. Hold guard for 2 seconds.
4. Slowly extend lead hand and return.
5. Slowly extend rear hand and return.
6. App checks framing, visibility, and approximate angle.

Calibration goals:

- Confirm full-body visibility
- Establish baseline guard
- Identify lead/rear side
- Estimate scale
- Establish camera angle confidence
- Reduce false positives

## Tests

### Jab Test

User performs 10 jabs from static stance.

Checks:

- Lead hand extension
- Lead hand return to guard
- Rear hand guard retention
- Lead elbow flare
- Pre-punch hand dip or shoulder hitch
- Punch path
- Stance stability
- Estimated jab speed

### Cross Test

User performs 10 crosses from static stance.

Checks:

- Rear hand extension
- Rear hand return to guard
- Lead hand guard retention
- Rear elbow flare
- Pre-punch telegraphing
- Shoulder and hip rotation estimate
- Overreach or forward lean
- Stance stability
- Estimated cross speed

### Jab-Cross Test

User performs 10 jab-cross combinations.

Checks:

- Combo rhythm
- Jab return before or during cross launch
- Rear hand guard during jab
- Lead hand recovery after cross
- Guard exposure during transition
- Elbow flare on either punch
- Telegraphing before either punch
- Stance stability
- Estimated jab and cross speed

## Core Metrics

All metrics should include confidence labels: High, Medium, or Low.

Do not show percentage confidence in V1.

### Guard Discipline

Measures whether hands stay near guard during and after strikes.

Example outputs:

- "Rear hand dropped on 6 of 10 jabs."
- "Lead hand returned cleanly on 8 of 10 crosses."

### Return-To-Guard Time

Measures time from max extension to guard recovery.

Example outputs:

- "Average jab return time: 310 ms."
- "Your cross return slowed after rep 6."

### Elbow Flare

Detects elbow movement outward before or during punch extension.

Example output:

- "Lead elbow flared before 4 of 10 jabs."

### Telegraphing

V1 telegraphing detection is limited to visible patterns:

- Hand dip before strike
- Elbow flare before strike
- Shoulder hitch before extension
- Excessive pre-punch torso lean

### Punch Path

Measures whether the punch travels in a relatively direct path from guard to extension.

### Stance Stability

Measures whether the user maintains a usable base during and after strikes.

### Estimated Punch Speed

Show speed as an estimate with confidence.

Example:

- "Estimated jab speed: 4.8 m/s"
- "+7% vs previous test" when baseline exists
- "Confidence: Medium"

Punch speed should be framed as an estimate because single-camera video cannot perfectly resolve depth.

## Results Experience

Results should be staged.

Stage 1: Summary

- Top 3 focus areas
- Strongest metric
- Lowest-confidence metric if relevant
- Clear next action

Stage 2: Metric Breakdown

- Guard discipline
- Return-to-guard time
- Telegraphing
- Elbow flare
- Punch path
- Stance stability
- Estimated speed

Stage 3: Issue Clips

Short clips showing detected moments such as:

- Rear hand drop
- Slow return
- Elbow flare
- Hand dip before jab
- Forward lean on cross

Clips are temporary and expire after the result session.

Stage 4: Drill Recommendations

Each recommendation should include:

- What happened
- Why it matters
- How to fix it
- One drill
- Suggested volume

## Feedback Tone

Tone should be technical, direct, and coach-like.

Principles:

- Be specific
- Tie feedback to evidence
- Avoid vague criticism
- Avoid false certainty
- Prioritize one to three fixes

Avoid a global form score in V1.

## Drill Library

Use a curated internal drill library. AI may select and explain drills, but should not invent unapproved drills.

Initial size: 15-25 drills.

Example issue mappings:

- `rear_hand_drops_on_jab` -> `rear_hand_guard_jab_drill`
- `slow_return_to_guard` -> `jab_return_metronome_drill`
- `elbow_flare` -> `straight_line_jab_drill`
- `hand_dip_telegraph` -> `no_dip_jab_drill`
- `overreach_on_cross` -> `cross_balance_reset_drill`
- `weak_cross_rotation` -> `slow_cross_hip_turn_drill`

## Technical Requirements

Video capture:

- In-app mobile web recording
- Camera permission flow
- Framing guide
- Stance-specific setup instructions
- Full-body visibility check where possible

Upload and processing:

- Upload video to server
- Process asynchronously
- Return results quickly for short tests
- Delete source video after analysis
- Generate temporary issue clips before deletion

Pose estimation:

- Use existing pose estimation models for V1
- Consider MediaPipe/BlazePose, MoveNet, or similar
- Do not train a custom pose model for V1

Analysis pipeline:

1. Receive video.
2. Validate quality and framing.
3. Extract frames.
4. Run pose estimation.
5. Smooth landmarks.
6. Detect stance and orientation.
7. Detect strike reps.
8. Segment reps.
9. Calculate metrics.
10. Assign confidence labels.
11. Identify top issues.
12. Generate issue clips.
13. Return results.
14. Delete original video.

## Pose Models And Video Processing

The MVP should treat pose estimation and video processing as separate layers.

- Pose estimation finds body landmarks.
- Video processing normalizes video, runs frame analysis, creates clips, and supports metric calculation.
- The Muay Thai interpretation layer turns landmarks into test-specific feedback.

### Recommended MVP Pose Model

Start with MediaPipe Pose Landmarker / BlazePose on the server side.

What it does:

- Detects body landmarks from video frames
- Outputs 33 pose landmarks
- Includes shoulders, elbows, wrists, hips, knees, ankles, heels, and foot index points
- Provides normalized image coordinates and estimated 3D/world coordinates
- Has paths for Python, web, Android, and iOS

Why it fits:

- Strong fit for fitness-style body tracking
- More landmarks than many lightweight models
- Useful for guard, elbow, wrist, hip, knee, ankle, and foot checks
- Gives the product a path toward native mobile later

Limitations:

- Single-camera 3D is estimated, not true measured depth
- Fast punches can create landmark jitter or motion blur
- Punch speed and rotation should remain confidence-labeled estimates

### Alternative Pose Models

#### MoveNet

What it does:

- Detects 17 body keypoints
- Commonly used for fast fitness and wellness pose tracking
- Has lightweight and more accurate model variants

Strengths:

- Fast
- Simple
- Good for basic upper-body tests

Limitations:

- Fewer landmarks than MediaPipe
- No detailed heel or foot-index landmarks
- Weaker for stance and footwork analysis

#### YOLO Pose / Ultralytics Pose

What it does:

- Detects people and pose keypoints
- Works well inside broader object detection workflows
- Could later support detecting gloves, bags, pads, or multiple people

Strengths:

- Strong general computer-vision ecosystem
- Useful if object detection becomes important later

Limitations:

- Usually fewer keypoints than MediaPipe
- Commercial licensing needs careful review before product use

#### OpenPose

What it does:

- Whole-body pose estimation with body, hands, face, and feet
- Can output many detailed keypoints

Strengths:

- Rich keypoint detail
- Historically proven pose-estimation system

Limitations:

- Heavier implementation
- More complicated deployment
- Commercial licensing may be less straightforward
- Likely overkill for the first MVP

### Video Processing Components

#### FFmpeg

FFmpeg should be used for video normalization and clip generation.

Responsibilities:

- Read common mobile video formats
- Normalize rotation, resolution, frame rate, and encoding
- Inspect video metadata with ffprobe
- Trim issue clips around detected timestamps
- Compress temporary result clips for playback

Example use cases:

- Convert uploaded video into a predictable analysis format
- Extract a 1-3 second clip around a rear-hand drop
- Create lightweight clips for the results screen

#### OpenCV

OpenCV should be used for frame-level processing and analysis utilities.

Responsibilities:

- Read video frame by frame
- Pass frames into the pose model
- Draw skeleton overlays for debugging and possible result clips
- Measure frame timestamps, coordinates, angles, and velocities
- Write annotated debug videos if needed

Example use cases:

- Run pose inference on every frame
- Calculate wrist velocity over time
- Calculate elbow angle and hand path
- Create visual debug overlays during development

### Pose Inference Layer

The pose inference layer converts frames into landmark time series.

Each frame should produce structured landmark data:

- Frame number
- Timestamp
- Landmark coordinates
- Landmark confidence/visibility
- Model-level detection confidence if available

Example output shape:

```json
{
  "frame": 124,
  "timestamp_ms": 4133,
  "left_wrist": {
    "x": 0.42,
    "y": 0.31,
    "z": -0.12,
    "confidence": 0.91
  },
  "right_elbow": {
    "x": 0.58,
    "y": 0.39,
    "z": -0.08,
    "confidence": 0.88
  }
}
```

### Landmark Smoothing

Landmark smoothing is required before calculating timing, speed, or form metrics.

Why it matters:

- Raw pose landmarks can jitter frame to frame
- Fast punches can create fake speed spikes
- Motion blur can make wrist tracking noisy
- Smoothing makes return time and speed estimates more stable

Possible approaches:

- Moving average
- Kalman filter
- One Euro filter
- Savitzky-Golay smoothing

The MVP can begin with a simple moving average or One Euro filter, then compare against raw landmarks during validation.

### Rep Detection

Rep detection segments each test into individual strikes.

For jab:

- Start: lead wrist leaves guard
- Peak: lead wrist reaches maximum extension
- End: lead wrist returns to guard

For cross:

- Start: rear wrist leaves guard
- Peak: rear wrist reaches maximum extension
- End: rear wrist returns to guard

For jab-cross:

- Detect lead-hand extension
- Detect transition into rear-hand extension
- Detect final recovery to guard
- Track whether guard is exposed during the transition

Rep detection should return per-rep timestamps so metrics and clips can reference specific moments.

### Metrics Engine

The metrics engine converts pose landmarks into coaching feedback.

Initial metrics should be rule-based, not machine-learning based.

Responsibilities:

- Detect hands-up/guard discipline
- Calculate return-to-guard time
- Detect elbow flare
- Detect visible telegraphing
- Estimate punch path
- Estimate punch speed
- Detect stance instability
- Assign confidence labels
- Select top issues for feedback

This layer is the main product differentiator. The pose model finds joints; the metrics engine decides what those joint patterns mean for Muay Thai beginners.

### Clip Extraction

Issue clips should connect feedback to visible evidence.

Clip extraction flow:

1. Metrics engine identifies an issue.
2. Issue includes test type, rep number, start timestamp, and end timestamp.
3. FFmpeg extracts a short clip around that timestamp.
4. Clip is labeled by issue type.
5. Clip is shown in the result session.
6. Clip expires after the session.

Example issue clip payload:

```json
{
  "issue": "rear_hand_drop",
  "test": "jab",
  "rep": 4,
  "start_ms": 8200,
  "end_ms": 10100
}
```

### Recommended First Technical Prototype

The first prototype should prove the core technical bet before building full product polish.

Scope:

- Upload one jab-test video
- Run MediaPipe Pose Landmarker server-side
- Use OpenCV to process frames
- Show skeleton overlay for debugging
- Detect lead wrist leaving and returning to guard
- Calculate return-to-guard time
- Detect rear hand dropping during jab
- Use FFmpeg to extract one issue clip

This prototype answers the most important early question: can the system reliably detect a few meaningful beginner striking issues from phone video?

## Privacy And Retention

V1 privacy promise:

- Videos are uploaded for analysis only
- Original videos are deleted after processing
- Issue clips are temporary and expire after the result session
- No persistent video storage
- No login or cloud profile in V1

## Edge Cases

Handle:

- User too close
- Feet out of frame
- Hands out of frame
- Poor lighting
- User turns away
- Low pose confidence
- Multiple people in frame
- Mirrored selfie camera
- Southpaw stance
- Loose clothing/gloves obscuring joints
- Low frame rate
- Rep detection failure
- Upload failure
- Processing timeout

## Success Metrics

Product metrics:

- Assessment completion rate
- Successful analysis rate
- Percentage of tests with high or medium confidence
- User-rated usefulness
- Retake rate
- Time from recording to results
- Issue clip view rate
- Drill start rate

Technical metrics:

- Pose detection success rate
- Rep detection accuracy
- False positive rate for hand drop
- False positive rate for elbow flare
- Speed estimate consistency under same setup
- Analysis latency
- Video deletion success rate

## Roadmap

Phase 1: constrained test MVP.

Phase 1.1: local progress and baseline comparison.

Phase 2: accounts, profiles, saved metrics, progress charts.

Phase 3: freestyle shadowboxing review.

Phase 4: hooks, basic footwork tests, defensive movement, then kicks/knees/elbows later.

Phase 5: coach dashboard and gym tools.

## Major Risks

- Measurement trust
- Camera setup variability
- Overclaiming coaching ability
- Drill quality
- Privacy concerns

## Open Questions

- Which pose model is best for accuracy and latency?
- What is acceptable analysis time for a 10-rep test?
- Should V1 include browser-local history?
- What exact thresholds define guard drop, elbow flare, and return-to-guard?
- How should mirrored camera recordings be handled?
- What is the minimum launch drill library?
- Can a coach review the first drill library and metric definitions?
- Should issue clips include pose overlay or raw video only?
- What backend infrastructure best supports temporary video processing and deletion?

## MVP Recommendation

Build the smallest version that proves whether AI-assisted Muay Thai form feedback is useful: mobile web, in-app recording, setup/calibration, jab/cross/jab-cross tests, server-side pose analysis, confidence-labeled metrics, temporary issue clips, curated drills, and no persistent video storage.

The core V1 question is whether the product can reliably detect a few meaningful beginner striking issues and give feedback users trust enough to retest.
