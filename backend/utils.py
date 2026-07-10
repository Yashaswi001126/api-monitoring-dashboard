"""
utils.py
--------
Small, reusable helper functions that don't belong to any single module.
Keeping them here avoids duplicating logic (e.g. uptime math) in both
monitor.py and crud.py.
"""

from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """
    Basic sanity check that a string looks like a real URL
    (has a scheme like 'http'/'https' and a network location).

    This catches obviously malformed input (e.g. "not-a-url") before
    we even attempt a network request, so we can log a clear
    "Invalid URL" error instead of a confusing low-level exception.
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except (ValueError, AttributeError):
        return False


def calculate_uptime_percent(total_checks: int, successful_checks: int) -> float:
    """
    Returns uptime as a percentage rounded to 2 decimals.
    Guards against division by zero when there's no data yet.
    """
    if total_checks == 0:
        return 0.0
    return round((successful_checks / total_checks) * 100, 2)


def calculate_average(values: list) -> float:
    """
    Returns the average of a list of numbers, rounded to 2 decimals.
    Returns 0.0 for an empty list instead of raising ZeroDivisionError.
    """
    values = [v for v in values if v is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
