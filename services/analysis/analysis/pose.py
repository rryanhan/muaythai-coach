from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


# A dataclass is a lightweight Python way to define a data container.
# frozen=True means once we create the object, we do not mutate it later.
@dataclass(frozen=True)
class Landmark:
    # MediaPipe normalized coordinates:
    # x=0 is left edge of image, x=1 is right edge.
    # y=0 is top of image, y=1 is bottom.
    # z is estimated depth, not a true measured distance from a single camera.
    name: str
    x: float
    y: float
    z: float | None
    confidence: float | None


@dataclass(frozen=True)
class PoseFrame:
    # One video frame plus whichever pose landmarks MediaPipe found in that frame.
    frame_index: int
    timestamp_ms: float
    landmarks: list[Landmark]

    def landmark_map(self) -> dict[str, Landmark]:
        # Most metric code wants "give me left_wrist" rather than looping through
        # all landmarks every time. This converts the list into a name lookup table.
        return {landmark.name: landmark for landmark in self.landmarks}


class PoseEstimator:
    """Interface for pose-estimation implementations.

    This lets the rest of our code depend on "something that estimates pose"
    instead of depending directly on MediaPipe forever. Later, we could add
    MoveNet or another model behind the same method shape.
    """

    def estimate_video(self, video_path: Path) -> list[PoseFrame]:
        raise NotImplementedError


class MediaPipePoseEstimator(PoseEstimator):
    """MediaPipe Pose wrapper that returns one structured record per video frame."""

    def __init__(
        self,
        model_path: Path | None = None,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        # The .task file is the actual downloaded MediaPipe model.
        # The Python package supplies the runtime; this file supplies the trained weights.
        default_model_path = (
            Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
        )
        self.model_path = model_path or default_model_path
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

    def estimate_video(self, video_path: Path) -> list[PoseFrame]:
        # These imports are intentionally local. Most analysis code only needs the
        # lightweight Landmark/PoseFrame dataclasses, and importing MediaPipe can
        # trigger slow native setup even when we are just reading cached JSON.
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
            VisionTaskRunningMode,
        )
        from mediapipe.tasks.python.vision.pose_landmarker import (
            PoseLandmark,
            PoseLandmarker,
            PoseLandmarkerOptions,
        )

        if not self.model_path.exists():
            raise ValueError(f"MediaPipe pose model does not exist: {self.model_path}")

        # OpenCV handles decoding the video file into individual image frames.
        # It does not understand Muay Thai or body pose; it is just our frame reader here.
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        # FPS lets us convert frame numbers into real timestamps. For example,
        # at 30fps, frame 30 is roughly 1000ms into the video.
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frames: list[PoseFrame] = []

        # The current mediapipe package exposes the newer Tasks API, which requires
        # an explicit .task model file and VIDEO running mode for timestamped frames.
        options = PoseLandmarkerOptions(
            # Force CPU inference. On some local Mac/sandbox setups MediaPipe tries
            # to initialize a Metal/GPU path and crashes before returning landmarks.
            base_options=BaseOptions(
                model_asset_path=str(self.model_path),
                delegate=BaseOptions.Delegate.CPU,
            ),
            running_mode=VisionTaskRunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=self.min_detection_confidence,
            min_pose_presence_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            output_segmentation_masks=False,
        )

        # The context manager opens MediaPipe's native resources and closes them
        # automatically when the block finishes, even if an error occurs.
        with PoseLandmarker.create_from_options(options) as pose:
            frame_index = 0
            while True:
                # capture.read() returns:
                # - ok: whether another frame was available
                # - frame: the actual image pixels for that video frame
                ok, frame = capture.read()
                if not ok:
                    break

                # OpenCV reads BGR images; MediaPipe expects RGB.
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms = int((frame_index / fps) * 1000.0)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                results = pose.detect_for_video(mp_image, timestamp_ms)
                landmarks: list[Landmark] = []

                # We keep empty frames too. That makes pose detection failures visible
                # in landmarks.json instead of hiding them.
                if results.pose_landmarks and results.pose_landmarks[0]:
                    # PoseLandmark is MediaPipe's ordered enum of body parts.
                    # results.pose_landmarks[0] is the first detected person's landmark list.
                    for landmark_name, landmark in zip(
                        PoseLandmark,
                        results.pose_landmarks[0],
                        strict=True,
                    ):
                        landmarks.append(
                            Landmark(
                                name=landmark_name.name.lower(),
                                x=float(landmark.x),
                                y=float(landmark.y),
                                z=float(landmark.z),
                                confidence=float(landmark.visibility),
                            )
                        )

                # Store one PoseFrame for every video frame, even when landmarks is empty.
                frames.append(
                    PoseFrame(
                        frame_index=frame_index,
                        timestamp_ms=float(timestamp_ms),
                        landmarks=landmarks,
                    )
                )
                frame_index += 1

        # Release the video file handle now that all frames have been read.
        capture.release()
        return frames


def pose_frames_to_json(frames: list[PoseFrame]) -> list[dict[str, Any]]:
    # Convert dataclass objects into plain dictionaries so json.dumps can write them.
    return [asdict(frame) for frame in frames]
