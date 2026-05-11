from dataclasses import asdict, dataclass
from typing import Any, Literal

from analysis.events import EventSummary, MotionEvent

StraightStrikeType = Literal["jab", "cross"]
StrikeConfidence = Literal["High", "Medium", "Low"]


@dataclass(frozen=True)
class StraightStrike:
    strike_type: StraightStrikeType
    start_ms: float
    peak_ms: float
    end_ms: float
    duration_ms: float
    peak_extension_ratio: float
    returned_to_guard: bool
    tracking_available_ratio: float
    confidence: StrikeConfidence
    notes: list[str]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StraightStrikeSummary:
    strikes: list[StraightStrike]
    counts: dict[str, int]
    high_or_medium_counts: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return {
            "strikes": [strike.to_json() for strike in self.strikes],
            "counts": self.counts,
            "high_or_medium_counts": self.high_or_medium_counts,
        }


def analyze_straight_strikes(event_summary: EventSummary) -> StraightStrikeSummary:
    strikes = [
        _strike_from_event(event)
        for event in event_summary.events
        if event.event_type in {"lead_hand_motion", "rear_hand_motion"}
    ]
    counts = _counts(strikes, include_low=True)
    high_or_medium_counts = _counts(strikes, include_low=False)
    return StraightStrikeSummary(
        strikes=strikes,
        counts=counts,
        high_or_medium_counts=high_or_medium_counts,
    )


def _strike_from_event(event: MotionEvent) -> StraightStrike:
    strike_type: StraightStrikeType = (
        "jab" if event.event_type == "lead_hand_motion" else "cross"
    )
    returned_to_guard = event.end_reason == "returned"
    confidence = _confidence(event, returned_to_guard)
    notes = _notes(event, returned_to_guard)
    return StraightStrike(
        strike_type=strike_type,
        start_ms=event.start_ms,
        peak_ms=event.peak_ms,
        end_ms=event.end_ms,
        duration_ms=event.duration_ms,
        peak_extension_ratio=event.peak_value,
        returned_to_guard=returned_to_guard,
        tracking_available_ratio=event.available_ratio,
        confidence=confidence,
        notes=notes,
    )


def _confidence(event: MotionEvent, returned_to_guard: bool) -> StrikeConfidence:
    if (
        event.peak_value >= 0.85
        and event.available_ratio >= 0.75
        and returned_to_guard
        and 80 <= event.duration_ms <= 1500
    ):
        return "High"
    if event.peak_value >= 0.6 and event.available_ratio >= 0.45:
        return "Medium"
    return "Low"


def _notes(event: MotionEvent, returned_to_guard: bool) -> list[str]:
    notes: list[str] = []
    if event.peak_value < 0.6:
        notes.append("short_extension_or_noise")
    if event.available_ratio < 0.45:
        notes.append("tracking_unavailable_for_much_of_event")
    if not returned_to_guard:
        notes.append(f"event_ended_by_{event.end_reason}")
    return notes


def _counts(strikes: list[StraightStrike], *, include_low: bool) -> dict[str, int]:
    counts = {"jab": 0, "cross": 0}
    for strike in strikes:
        if include_low or strike.confidence != "Low":
            counts[strike.strike_type] += 1
    return counts
