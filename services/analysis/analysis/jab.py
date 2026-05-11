from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Literal

from analysis.pose import Landmark, PoseFrame

Stance = Literal["orthodox", "southpaw"]
MAX_JAB_DURATION_MS = 1500.0
# Normal guard movement in the clean 60fps clip stayed under ~0.04, while the
# first obvious lead-hand dip landed around 0.06. Keep the threshold between them.
HAND_DIP_THRESHOLD = 0.055


@dataclass(frozen=True)
class JabRep:
    # One detected jab, represented by the timestamps we need for metrics and clips.
    rep_number: int
    start_ms: float
    peak_ms: float
    end_ms: float
    extension_time_ms: float
    extension_speed_normalized: float
    peak_extension_velocity_normalized: float
    return_time_ms: float
    rear_hand_dropped: bool
    hand_dip_telegraph: bool
    pre_jab_dip_normalized: float
    timing_confidence: str


@dataclass(frozen=True)
class JabMetrics:
    detected_reps: int
    rear_hand_drops: int
    hand_dip_telegraphs: int
    average_extension_time_ms: float | None
    average_extension_speed_normalized: float | None
    average_peak_extension_velocity_normalized: float | None
    average_return_time_ms: float | None
    confidence: str
    reps: list[JabRep]

    def to_json(self) -> dict[str, Any]:
        return {
            "detected_reps": self.detected_reps,
            "rear_hand_drops": self.rear_hand_drops,
            "hand_dip_telegraphs": self.hand_dip_telegraphs,
            "average_extension_time_ms": self.average_extension_time_ms,
            "average_extension_speed_normalized": self.average_extension_speed_normalized,
            "average_peak_extension_velocity_normalized": (
                self.average_peak_extension_velocity_normalized
            ),
            "average_return_time_ms": self.average_return_time_ms,
            "confidence": self.confidence,
            "reps": [asdict(rep) for rep in self.reps],
        }


def analyze_jab_landmarks(frames: list[PoseFrame], stance: Stance = "orthodox") -> JabMetrics:
    # Orthodox means left hand jabs and right hand protects guard.
    # Southpaw flips those roles, but the rest of the math stays the same.
    lead_wrist_name = "left_wrist" if stance == "orthodox" else "right_wrist"
    rear_wrist_name = "right_wrist" if stance == "orthodox" else "left_wrist"
    lead_shoulder_name = "left_shoulder" if stance == "orthodox" else "right_shoulder"
    rear_shoulder_name = "right_shoulder" if stance == "orthodox" else "left_shoulder"

    samples = [
        _JabSample.from_frame(
            frame,
            lead_wrist_name,
            rear_wrist_name,
            lead_shoulder_name,
            rear_shoulder_name,
        )
        for frame in frames
    ]
    valid_samples = [sample for sample in samples if sample is not None]
    if len(valid_samples) < 15:
        return JabMetrics(0, 0, 0, None, None, None, None, "Low", [])

    valid_samples = _smooth_samples(valid_samples)

    # Instead of trusting only the first frames, estimate "guard" from the lowest
    # lead-hand extension values. This is more forgiving if the clip starts late.
    extension_values = [sample.lead_extension for sample in valid_samples]
    guard_sample_count = max(5, len(extension_values) // 5)
    guard_extension = mean(sorted(extension_values)[:guard_sample_count])

    # Same idea for the rear hand: use the highest/cleanest guard position as baseline.
    # In image coordinates, lower on screen means a larger y value.
    rear_y_values = [sample.rear_y for sample in valid_samples]
    guard_rear_y = mean(sorted(rear_y_values)[:guard_sample_count])
    # Use a high percentile instead of the absolute max. A single bad wrist jump can
    # otherwise make every real jab look too small to cross the extension threshold.
    max_extension = _percentile(extension_values, 0.95)
    travel = max_extension - guard_extension

    if travel < 0.08:
        return JabMetrics(0, 0, 0, None, None, None, None, "Low", [])

    # Thresholds are percentages of the observed jab travel in this clip.
    # They are deliberately heuristic for now and will be tuned with your real videos.
    start_threshold = guard_extension + travel * 0.42
    peak_threshold = guard_extension + travel * 0.68
    return_threshold = guard_extension + travel * 0.38
    rear_drop_threshold = guard_rear_y + 0.055
    start_velocity_threshold = travel * 1.6
    return_velocity_threshold = -travel * 1.0

    reps: list[JabRep] = []
    state = "guard"
    start_index = 0
    peak_index = 0
    peak_extension = -1.0
    rear_drop_seen = False

    # Simple state machine:
    # guard -> extending when lead hand leaves guard
    # extending -> returning once it reaches a strong extension
    # returning -> guard once it comes back near the baseline
    for index, sample in enumerate(valid_samples):
        current_rep_duration_ms = sample.timestamp_ms - valid_samples[start_index].timestamp_ms
        if state != "guard" and current_rep_duration_ms > MAX_JAB_DURATION_MS:
            state = "guard"
            peak_extension = -1.0
            rear_drop_seen = False

        if (
            state == "guard"
            and sample.lead_extension > start_threshold
            and sample.extension_velocity > start_velocity_threshold
        ):
            state = "extending"
            start_index = index
            peak_index = index
            peak_extension = sample.lead_extension
            rear_drop_seen = sample.rear_y > rear_drop_threshold
            continue

        if state == "extending":
            if sample.lead_extension > peak_extension:
                peak_extension = sample.lead_extension
                peak_index = index
            rear_drop_seen = rear_drop_seen or sample.rear_y > rear_drop_threshold
            if (
                sample.lead_extension > peak_threshold
                and sample.extension_velocity <= return_velocity_threshold
            ):
                state = "returning"
            continue

        if state == "returning":
            if sample.lead_extension > peak_extension:
                peak_extension = sample.lead_extension
                peak_index = index
            rear_drop_seen = rear_drop_seen or sample.rear_y > rear_drop_threshold
            if sample.lead_extension < return_threshold:
                start = valid_samples[start_index]
                peak = valid_samples[peak_index]
                end = sample
                rep_duration_ms = end.timestamp_ms - start.timestamp_ms
                if 120 < rep_duration_ms <= MAX_JAB_DURATION_MS:
                    extension_time_ms = max(0.0, peak.timestamp_ms - start.timestamp_ms)
                    timing_confidence = _timing_confidence(start, peak, end)
                    pre_jab_dip = _pre_jab_dip(valid_samples, start_index)
                    rep = JabRep(
                        rep_number=len(reps) + 1,
                        start_ms=start.timestamp_ms,
                        peak_ms=peak.timestamp_ms,
                        end_ms=end.timestamp_ms,
                        extension_time_ms=extension_time_ms,
                        extension_speed_normalized=_extension_speed(
                            start.lead_extension,
                            peak.lead_extension,
                            extension_time_ms,
                        ),
                        peak_extension_velocity_normalized=_peak_extension_velocity(
                            valid_samples[start_index : index + 1]
                        ),
                        return_time_ms=max(0.0, end.timestamp_ms - peak.timestamp_ms),
                        rear_hand_dropped=rear_drop_seen,
                        hand_dip_telegraph=pre_jab_dip >= HAND_DIP_THRESHOLD,
                        pre_jab_dip_normalized=round(pre_jab_dip, 3),
                        timing_confidence=timing_confidence,
                    )
                    if timing_confidence != "Low":
                        reps.append(rep)
                state = "guard"

    average_return = mean(rep.return_time_ms for rep in reps) if reps else None
    average_extension_time = mean(rep.extension_time_ms for rep in reps) if reps else None
    average_extension_speed = (
        mean(rep.extension_speed_normalized for rep in reps if rep.extension_speed_normalized > 0)
        if reps
        else None
    )
    average_peak_extension_velocity = (
        mean(
            rep.peak_extension_velocity_normalized
            for rep in reps
            if rep.peak_extension_velocity_normalized > 0
        )
        if reps
        else None
    )
    confidence = _confidence_label(len(valid_samples), len(frames), len(reps))
    return JabMetrics(
        detected_reps=len(reps),
        rear_hand_drops=sum(1 for rep in reps if rep.rear_hand_dropped),
        hand_dip_telegraphs=sum(1 for rep in reps if rep.hand_dip_telegraph),
        average_extension_time_ms=(
            round(average_extension_time, 1) if average_extension_time is not None else None
        ),
        average_extension_speed_normalized=(
            round(average_extension_speed, 3) if average_extension_speed is not None else None
        ),
        average_peak_extension_velocity_normalized=(
            round(average_peak_extension_velocity, 3)
            if average_peak_extension_velocity is not None
            else None
        ),
        average_return_time_ms=round(average_return, 1) if average_return is not None else None,
        confidence=confidence,
        reps=reps,
    )


@dataclass(frozen=True)
class _JabSample:
    # Reduced per-frame values for the jab rules. The full landmarks are kept in
    # landmarks.json, but the metrics only need these derived measurements.
    timestamp_ms: float
    lead_extension: float
    lead_y: float
    rear_y: float
    extension_velocity: float
    lead_confidence: float
    rear_confidence: float

    @classmethod
    def from_frame(
        cls,
        frame: PoseFrame,
        lead_wrist_name: str,
        rear_wrist_name: str,
        lead_shoulder_name: str,
        rear_shoulder_name: str,
    ) -> "_JabSample | None":
        landmarks = frame.landmark_map()
        lead_wrist = _visible(landmarks.get(lead_wrist_name))
        rear_wrist = _visible(landmarks.get(rear_wrist_name))
        lead_shoulder = _visible(landmarks.get(lead_shoulder_name))
        rear_shoulder = _visible(landmarks.get(rear_shoulder_name))
        if not lead_wrist or not rear_wrist or not lead_shoulder or not rear_shoulder:
            return None

        # For the first prototype, extension is horizontal wrist movement away from
        # the lead shoulder in normalized image coordinates.
        lead_extension = abs(lead_wrist.x - lead_shoulder.x)
        # Image y increases downward, so a larger wrist y means the rear hand dropped.
        rear_y = rear_wrist.y - rear_shoulder.y
        return cls(
            timestamp_ms=frame.timestamp_ms,
            lead_extension=lead_extension,
            lead_y=lead_wrist.y - lead_shoulder.y,
            rear_y=rear_y,
            extension_velocity=0.0,
            lead_confidence=lead_wrist.confidence or 0.0,
            rear_confidence=rear_wrist.confidence or 0.0,
        )


def _visible(landmark: Landmark | None, min_confidence: float = 0.35) -> Landmark | None:
    # Low-confidence landmarks are ignored so a shaky wrist detection does not
    # silently become a confident coaching claim.
    if landmark is None:
        return None
    if (landmark.confidence or 0.0) < min_confidence:
        return None
    return landmark


def _confidence_label(valid_frame_count: int, total_frame_count: int, rep_count: int) -> str:
    # V1 shows High/Medium/Low only. No percentages, because the signal is still approximate.
    if total_frame_count == 0:
        return "Low"
    visible_ratio = valid_frame_count / total_frame_count
    if visible_ratio >= 0.8 and 8 <= rep_count <= 12:
        return "High"
    if visible_ratio >= 0.55 and rep_count >= 3:
        return "Medium"
    return "Low"


def _smooth_samples(samples: list[_JabSample], window_radius: int = 1) -> list[_JabSample]:
    smoothed: list[_JabSample] = []
    for index, sample in enumerate(samples):
        window = samples[max(0, index - window_radius) : index + window_radius + 1]
        smoothed.append(
            _JabSample(
                timestamp_ms=sample.timestamp_ms,
                lead_extension=mean(window_sample.lead_extension for window_sample in window),
                lead_y=mean(window_sample.lead_y for window_sample in window),
                rear_y=mean(window_sample.rear_y for window_sample in window),
                extension_velocity=0.0,
                lead_confidence=sample.lead_confidence,
                rear_confidence=sample.rear_confidence,
            )
        )
    return _with_extension_velocity(smoothed)


def _with_extension_velocity(samples: list[_JabSample]) -> list[_JabSample]:
    if not samples:
        return []

    with_velocity = [
        _JabSample(
            timestamp_ms=samples[0].timestamp_ms,
            lead_extension=samples[0].lead_extension,
            lead_y=samples[0].lead_y,
            rear_y=samples[0].rear_y,
            extension_velocity=0.0,
            lead_confidence=samples[0].lead_confidence,
            rear_confidence=samples[0].rear_confidence,
        )
    ]
    for previous, sample in zip(samples, samples[1:], strict=False):
        delta_seconds = (sample.timestamp_ms - previous.timestamp_ms) / 1000.0
        velocity = (
            (sample.lead_extension - previous.lead_extension) / delta_seconds
            if delta_seconds > 0
            else 0.0
        )
        with_velocity.append(
            _JabSample(
                timestamp_ms=sample.timestamp_ms,
                lead_extension=sample.lead_extension,
                lead_y=sample.lead_y,
                rear_y=sample.rear_y,
                extension_velocity=velocity,
                lead_confidence=sample.lead_confidence,
                rear_confidence=sample.rear_confidence,
            )
        )
    return with_velocity


def _extension_speed(
    start_extension: float,
    peak_extension: float,
    extension_time_ms: float,
) -> float:
    if extension_time_ms <= 0:
        return 0.0
    return max(0.0, peak_extension - start_extension) / (extension_time_ms / 1000.0)


def _peak_extension_velocity(samples: list[_JabSample]) -> float:
    positive_velocities = [
        sample.extension_velocity for sample in samples if sample.extension_velocity > 0
    ]
    if not positive_velocities:
        return 0.0
    return round(_percentile(positive_velocities, 0.95), 3)


def _timing_confidence(start: _JabSample, peak: _JabSample, end: _JabSample) -> str:
    min_confidence = min(start.lead_confidence, peak.lead_confidence, end.lead_confidence)
    extension_time_ms = peak.timestamp_ms - start.timestamp_ms
    return_time_ms = end.timestamp_ms - peak.timestamp_ms
    if min_confidence >= 0.75 and extension_time_ms >= 60 and return_time_ms >= 100:
        return "High"
    if min_confidence >= 0.45 and extension_time_ms >= 30 and return_time_ms >= 60:
        return "Medium"
    return "Low"


def _pre_jab_dip(samples: list[_JabSample], start_index: int) -> float:
    start = samples[start_index]
    guard_window = [
        sample.lead_y
        for sample in samples
        if start.timestamp_ms - 700 <= sample.timestamp_ms < start.timestamp_ms - 350
    ]
    pre_jab_window = [
        sample.lead_y
        for sample in samples
        if start.timestamp_ms - 300 <= sample.timestamp_ms < start.timestamp_ms
    ]
    if not guard_window or not pre_jab_window:
        return 0.0

    # Image y increases downward, so a positive value means the lead hand dipped.
    return max(0.0, max(pre_jab_window) - mean(guard_window))


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]
