"""Interpret Nightscout records without Home Assistant dependencies."""

from datetime import datetime, timedelta, timezone
from math import isfinite

MAX_AGE = timedelta(minutes=15)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        parsed = float(value)
    except (ValueError, OverflowError):
        return None
    return parsed if isfinite(parsed) else None


def timestamp(value):
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value / 1000, timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed
    except (ValueError, OverflowError, OSError):
        pass
    return None


def mapping(value):
    return value if isinstance(value, dict) else {}


def fresh(value, now):
    return value is not None and now - MAX_AGE <= value <= now + timedelta(minutes=2)


def parse(entries, statuses, now):
    """Return current values, using the latest record per telemetry type."""
    data = {}
    if entries:
        entry = entries[0]
        measured = timestamp(entry.get("date")) or timestamp(entry.get("dateString"))
        data["glucose_timestamp"] = measured
        glucose = number(entry.get("sgv"))
        if fresh(measured, now) and glucose is not None and glucose >= 39:
            data["glucose"] = glucose
            for previous in entries[1:]:
                previous_time = timestamp(previous.get("date")) or timestamp(
                    previous.get("dateString")
                )
                if previous_time is None or previous_time >= measured:
                    continue
                previous_glucose = number(previous.get("sgv"))
                if (
                    fresh(previous_time, now)
                    and previous_glucose is not None
                    and previous_glucose >= 39
                ):
                    data["glucose_delta"] = glucose - previous_glucose
                break
            if isinstance(entry.get("direction"), str):
                data["trend"] = entry["direction"]

    for key in ("loop", "pump", "uploader", "override"):
        candidates = []
        for status in statuses:
            section = mapping(status.get(key))
            created = timestamp(status.get("created_at"))
            if section and created is not None:
                candidates.append((created, section))
        if not candidates:
            continue
        created, section = max(candidates, key=lambda candidate: candidate[0])
        if not fresh(created, now):
            continue

        if key in ("uploader", "override"):
            reported = timestamp(section.get("timestamp")) or created
            if not fresh(reported, now):
                continue
            if key == "override":
                active = section.get("active")
                if isinstance(active, bool):
                    data["override_active"] = active
                continue
            charging = section.get("isCharging")
            if isinstance(charging, bool):
                data["uploader_charging"] = charging
            battery = number(section.get("battery"))
            if battery is not None and 0 <= battery <= 100:
                data["uploader_battery"] = battery
            continue

        if key == "pump":
            pump_time = timestamp(section.get("clock")) or created
            data["pump_timestamp"] = pump_time
            if fresh(pump_time, now):
                model = section.get("model")
                if isinstance(model, str) and model.strip():
                    data["pump_model"] = model.strip()
                status = mapping(section.get("status"))
                for field in ("suspended", "bolusing"):
                    value = section.get(field, status.get(field))
                    if isinstance(value, bool):
                        data[f"pump_{field}"] = value
                reservoir = number(section.get("reservoir"))
                battery = number(mapping(section.get("battery")).get("percent"))
                if reservoir is not None and reservoir >= 0:
                    data["reservoir"] = reservoir
                if battery is not None and 0 <= battery <= 100:
                    data["pump_battery"] = battery
            continue

        loop_time = timestamp(section.get("timestamp")) or created
        data["loop_timestamp"] = loop_time
        if not fresh(loop_time, now):
            continue
        version = section.get("version")
        if isinstance(version, str) and version.strip():
            data["loop_version"] = version.strip()
        points = forecast_points(section.get("predicted"), now)
        if points:
            data["glucose_forecast"] = points[-1]["mg_dl"]
            data["forecast_points"] = points
        for metric in ("iob", "cob"):
            reading = mapping(section.get(metric))
            if fresh(timestamp(reading.get("timestamp")) or loop_time, now):
                data[metric] = number(reading.get(metric))
        if section.get("failureReason"):
            data["loop_ok"] = False
        elif timestamp(section.get("timestamp")) is not None:
            data["loop_ok"] = True
    return data


def forecast_points(predicted, now):
    """Return timestamped Loop forecast points in mg/dL."""
    predicted = mapping(predicted)
    start = timestamp(predicted.get("startDate"))
    values = predicted.get("values")
    if not fresh(start, now) or not isinstance(values, list):
        return []

    points = []
    for index, value in enumerate(values):
        glucose = number(value)
        if glucose is not None and glucose > 0:
            point_time = start + timedelta(minutes=5 * index)
            points.append({"timestamp": point_time.isoformat(), "mg_dl": glucose})
    return points


def event_age_hours(records, event_types, now):
    """Return hours since the latest matching event at or before now."""
    latest = None
    for record in records:
        if record.get("eventType") not in event_types:
            continue
        occurred = timestamp(record.get("created_at"))
        if occurred is not None and occurred <= now and (latest is None or occurred > latest):
            latest = occurred
    if latest is None:
        return None
    return (now - latest).total_seconds() / 3600
