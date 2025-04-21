# forest_app/core/utils.py

from forest_app.config.constants import MAGNITUDE_MIN_VALUE, MAGNITUDE_MAX_VALUE

def normalize_magnitude(raw: float) -> float:
    """
    Convert a raw 1–10 magnitude into a 0–1 normalized value for scoring
    without altering the raw magnitude itself.
    """
    span = MAGNITUDE_MAX_VALUE - MAGNITUDE_MIN_VALUE
    if span <= 0:
        return 0.0
    norm = (raw - MAGNITUDE_MIN_VALUE) / span
    return max(0.0, min(1.0, norm))


