"""Bounded age of a real GDK event timestamp, not pen-to-pixel latency."""
import math


def event_age_ms(timestamp, monotonic_ms):
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or not 0 < timestamp < 2**32:
        return None
    if isinstance(monotonic_ms, bool) or not isinstance(monotonic_ms, (int, float)) or not math.isfinite(monotonic_ms) or monotonic_ms < 0:
        return None
    age = (int(monotonic_ms) - timestamp) % (2**32)
    # Reject incompatible clock domains and implausibly stale timestamps.
    return age if age <= 30000 else None
