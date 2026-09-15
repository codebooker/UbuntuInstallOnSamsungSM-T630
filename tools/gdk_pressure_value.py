"""Normalize GTK3 introspection's nullable pressure output, without logging input."""
import math


def pressure_value(result):
    # Depending on introspection annotations, get_axis() returns nullable
    # double or (success, double). In particular, zero is valid pressure.
    if isinstance(result, tuple):
        if len(result) != 2 or result[0] is not True:
            return None
        result = result[1]
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        return None
    value = float(result)
    return value if math.isfinite(value) and 0 <= value <= 1 else None
