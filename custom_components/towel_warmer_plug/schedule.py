"""Pure schedule evaluation for the towel warmer."""
from datetime import datetime, time, timedelta

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(value)


def is_in_schedule(
    now: datetime,
    weekdays: list[str],
    windows: list[tuple[str | time, str | time]],
) -> bool:
    """Check all windows, anchoring overnight windows to their start day."""
    today = WEEKDAYS[now.weekday()]
    yesterday = WEEKDAYS[(now.weekday() - 1) % 7]
    current = now.time().replace(tzinfo=None)
    for start_value, end_value in windows:
        start, end = _parse_time(start_value), _parse_time(end_value)
        if start == end:
            if today in weekdays:
                return True
        elif start < end:
            if today in weekdays and start <= current < end:
                return True
        elif (today in weekdays and current >= start) or (
            yesterday in weekdays and current < end
        ):
            return True
    return False
