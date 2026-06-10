from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

READ_HINTS = (
    "what's on", "what is on", "what do i have", "do i have", "am i free",
    "calendar", "schedule", "agenda", "meetings", "meeting", "appointments",
)
WRITE_HINTS = (
    "move", "reschedule", "create", "add", "book", "cancel", "delete", "schedule a",
)


def is_calendar_read_intent(text: str) -> bool:
    normalized = text.lower().strip()
    if not normalized:
        return False
    if any(hint in normalized for hint in WRITE_HINTS):
        return False
    return any(hint in normalized for hint in READ_HINTS)


def get_time_window(text: str, timezone_name: str) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    normalized = text.lower()

    if "tomorrow" in normalized:
        day = now.date() + timedelta(days=1)
        return _day_window(day, tz) + ("tomorrow",)

    if "today" in normalized:
        start = now
        end = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=tz)
        return start, end, "today"

    if "next week" in normalized:
        start_date = now.date() + timedelta(days=(7 - now.weekday()))
        end_date = start_date + timedelta(days=7)
        return _range_window(start_date, end_date, tz) + ("next week",)

    if "this week" in normalized or "week" in normalized:
        start = now
        end_date = now.date() + timedelta(days=(7 - now.weekday()))
        end = datetime.combine(end_date, time.min, tzinfo=tz)
        return start, end, "this week"

    if "weekend" in normalized:
        days_until_saturday = (5 - now.weekday()) % 7
        start_date = now.date() + timedelta(days=days_until_saturday)
        end_date = start_date + timedelta(days=2)
        return _range_window(start_date, end_date, tz) + ("this weekend",)

    end = now + timedelta(days=7)
    return now, end, "the next seven days"


def _day_window(day, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, tzinfo=tz),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz),
    )


def _range_window(start_date, end_date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_date, time.min, tzinfo=tz),
        datetime.combine(end_date, time.min, tzinfo=tz),
    )
