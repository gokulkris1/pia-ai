from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from calendar_agent.google_client import read_events

CONFIRM_HINTS = {
    "yes", "yep", "yeah", "sure", "confirm", "confirmed", "do it", "go ahead",
    "please do", "that's right", "that is right", "correct", "ok", "okay",
}
DECLINE_HINTS = {
    "no", "nope", "cancel", "don't", "do not", "stop", "leave it", "not now", "never mind",
}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def is_confirmation(text: str) -> bool:
    normalized = _normalize(text)
    return any(hint in normalized for hint in CONFIRM_HINTS)


def is_decline(text: str) -> bool:
    normalized = _normalize(text)
    return any(hint in normalized for hint in DECLINE_HINTS)


def is_calendar_write_intent(text: str) -> bool:
    normalized = _normalize(text)
    return any(hint in normalized for hint in ("move", "reschedule", "create", "add", "book", "cancel", "delete", "schedule"))


def propose_calendar_write(project_root, user_id: str, text: str, timezone_name: str) -> dict[str, Any]:
    normalized = _normalize(text)
    tz = ZoneInfo(timezone_name)

    if any(word in normalized for word in ("cancel", "delete")):
        return _propose_cancel(project_root, user_id, text, tz)

    if any(word in normalized for word in ("move", "reschedule")):
        return _propose_move(project_root, user_id, text, tz)

    return _propose_create(text, tz)


def execute_calendar_action(service, proposal: dict[str, Any]) -> str:
    action = proposal.get("action")
    if action == "create":
        event = service.events().insert(calendarId="primary", body={
            "summary": proposal["title"],
            "start": {"dateTime": proposal["start"], "timeZone": proposal["timezone"]},
            "end": {"dateTime": proposal["end"], "timeZone": proposal["timezone"]},
        }).execute()
        title = event.get("summary") or proposal["title"]
        return f"Done — {title} is on your calendar for {_format_dt(proposal['start'])}."

    if action == "move":
        event_id = proposal["event_id"]
        service.events().patch(calendarId="primary", eventId=event_id, body={
            "start": {"dateTime": proposal["new_start"], "timeZone": proposal["timezone"]},
            "end": {"dateTime": proposal["new_end"], "timeZone": proposal["timezone"]},
        }).execute()
        return f"Done — moved {proposal['event_title']} to {_format_dt(proposal['new_start'])}."

    if action == "cancel":
        service.events().delete(calendarId="primary", eventId=proposal["event_id"]).execute()
        return f"Done — cancelled {proposal['event_title']}."

    raise ValueError("Unsupported calendar action")


def _propose_create(text: str, tz: ZoneInfo) -> dict[str, Any]:
    start = _target_datetime(text, tz)
    if not start:
        return _needs_detail("What time should I put that on your calendar for?")

    duration = _duration_from_text(text) or timedelta(hours=1)
    end = start + duration
    title = _title_from_create_text(text) or "Calendar event"
    prompt = f"Add {title} to your calendar for {_format_dt(start)} — shall I?"
    return {
        "action": "create",
        "title": title,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": tz.key,
        "confirmation_prompt": prompt,
    }


def _propose_move(project_root, user_id: str, text: str, tz: ZoneInfo) -> dict[str, Any]:
    times = _times_from_text(text, tz)
    if len(times) < 2:
        return _needs_detail("What time should I move it from and to?")

    source_time, target_time = times[0], times[1]
    event = _find_event(project_root, user_id, text, tz, source_time)
    if not event:
        return _needs_detail(f"I couldn't find a calendar event at {_format_time(source_time)}. Which event should I move?")

    old_start = _event_start(event)
    old_end = _event_end(event) or (old_start + timedelta(hours=1) if old_start else None)
    if not old_start or not old_end:
        return _needs_detail("I found the event, but its time is unclear. Which event should I move?")

    new_start = datetime.combine(old_start.date(), target_time, tzinfo=tz)
    if new_start < datetime.now(tz) and "tomorrow" in _normalize(text):
        new_start = new_start + timedelta(days=1)
    new_end = new_start + (old_end - old_start)
    title = event.get("summary") or "Untitled event"
    prompt = f"Move {title} from {_format_dt(old_start)} to {_format_dt(new_start)} — shall I?"
    return {
        "action": "move",
        "event_id": event["id"],
        "event_title": title,
        "old_start": old_start.isoformat(),
        "old_end": old_end.isoformat(),
        "new_start": new_start.isoformat(),
        "new_end": new_end.isoformat(),
        "timezone": tz.key,
        "confirmation_prompt": prompt,
    }


def _propose_cancel(project_root, user_id: str, text: str, tz: ZoneInfo) -> dict[str, Any]:
    source_time = (_times_from_text(text, tz) or [None])[0]
    event = _find_event(project_root, user_id, text, tz, source_time)
    if not event:
        detail = f" at {_format_time(source_time)}" if source_time else ""
        return _needs_detail(f"I couldn't find the calendar event{detail}. Which event should I cancel?")

    title = event.get("summary") or "Untitled event"
    start = _event_start(event)
    when = f" at {_format_dt(start)}" if start else ""
    prompt = f"Cancel {title}{when} — shall I?"
    return {
        "action": "cancel",
        "event_id": event["id"],
        "event_title": title,
        "event_start": start.isoformat() if start else None,
        "timezone": tz.key,
        "confirmation_prompt": prompt,
    }


def _find_event(project_root, user_id: str, text: str, tz: ZoneInfo, source_time: time | None) -> dict[str, Any] | None:
    start, end = _search_window(text, tz)
    events = read_events(project_root, user_id, start, end)
    title_hint = _title_hint(text)

    candidates = []
    for event in events:
        event_start = _event_start(event)
        if not event_start:
            continue
        if source_time and (event_start.hour, event_start.minute) != (source_time.hour, source_time.minute):
            continue
        if title_hint and title_hint not in _normalize(event.get("summary") or ""):
            continue
        candidates.append(event)

    return candidates[0] if len(candidates) == 1 else None


def _search_window(text: str, tz: ZoneInfo) -> tuple[datetime, datetime]:
    now = datetime.now(tz)
    normalized = _normalize(text)
    if "tomorrow" in normalized:
        start_date = now.date() + timedelta(days=1)
        return _day_window(start_date, tz)
    if "today" in normalized:
        return now, datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=tz)
    for name, weekday in WEEKDAYS.items():
        if name in normalized:
            days = (weekday - now.weekday()) % 7
            start_date = now.date() + timedelta(days=days)
            return _day_window(start_date, tz)
    return now, now + timedelta(days=14)


def _target_datetime(text: str, tz: ZoneInfo) -> datetime | None:
    times = _times_from_text(text, tz)
    if not times:
        return None
    target_time = times[-1]
    target_date = _target_date(text, tz)
    return datetime.combine(target_date, target_time, tzinfo=tz)


def _target_date(text: str, tz: ZoneInfo):
    now = datetime.now(tz)
    normalized = _normalize(text)
    if "tomorrow" in normalized:
        return now.date() + timedelta(days=1)
    if "today" in normalized:
        return now.date()
    for name, weekday in WEEKDAYS.items():
        if name in normalized:
            return now.date() + timedelta(days=(weekday - now.weekday()) % 7)
    return now.date()


def _times_from_text(text: str, tz: ZoneInfo) -> list[time]:
    del tz
    matches = re.findall(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", _normalize(text))
    values = []
    for hour_raw, minute_raw, meridiem in matches:
        hour = int(hour_raw)
        minute = int(minute_raw or "0")
        if hour > 24 or minute > 59:
            continue
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        elif not meridiem and 1 <= hour <= 7:
            hour += 12
        if hour == 24:
            hour = 0
        values.append(time(hour=hour, minute=minute))
    return values


def _duration_from_text(text: str) -> timedelta | None:
    match = re.search(r"\bfor\s+(\d+)\s*(hour|hours|hr|hrs|minute|minutes|min|mins)\b", _normalize(text))
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    return timedelta(hours=amount) if unit.startswith(("hour", "hr")) else timedelta(minutes=amount)


def _title_from_create_text(text: str) -> str:
    cleaned = re.sub(r"\b(add|create|book|schedule)\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(to my|on my|in my)?\s*calendar\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(at|for)\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    return cleaned[:80]


def _title_hint(text: str) -> str:
    normalized = _normalize(text)
    normalized = re.sub(r"\b(move|reschedule|cancel|delete|my|the|meeting|event|appointment|from|to|at|today|tomorrow)\b", " ", normalized)
    normalized = re.sub(r"\d{1,2}(:\d{2})?\s*(am|pm)?", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _event_start(event: dict[str, Any]) -> datetime | None:
    return _parse_event_datetime(event.get("start", {}))


def _event_end(event: dict[str, Any]) -> datetime | None:
    return _parse_event_datetime(event.get("end", {}))


def _parse_event_datetime(value: dict[str, Any]) -> datetime | None:
    raw = value.get("dateTime") or value.get("date")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _day_window(day, tz: ZoneInfo) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, tzinfo=tz),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz),
    )


def _needs_detail(reply: str) -> dict[str, Any]:
    return {"action": "needs_detail", "reply": reply}


def _format_dt(value: datetime | str) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%A %-I:%M %p").replace("AM", "am").replace("PM", "pm")


def _format_time(value: time | None) -> str:
    if value is None:
        return "that time"
    return value.strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")


def _normalize(text: str) -> str:
    return text.lower().strip()
