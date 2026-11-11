"""Exercise the Nightscout parser with synthetic records."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import unittest

# Load the parser directly so tests do not import the Home Assistant entry point.
parser_path = (
    Path(__file__).resolve().parents[1]
    / "custom_components/nightscout_extended/data.py"
)
parser = runpy.run_path(str(parser_path))
parse = parser["parse"]
event_age_hours = parser["event_age_hours"]

NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(minutes=2)).isoformat()
STALE = (NOW - timedelta(minutes=16)).isoformat()


class ParserTest(unittest.TestCase):
    def test_current_glucose_loop_and_pump(self):
        data = parse(
            [{"date": NOW.timestamp() * 1000, "sgv": 105, "direction": "Flat"}],
            [
                {"created_at": RECENT, "uploader": {"battery": 99}},
                {"created_at": RECENT, "pump": {"reservoir": 0, "battery": {"percent": 35}}},
                {
                    "created_at": RECENT,
                    "loop": {"timestamp": RECENT, "iob": {"iob": -0.1}, "cob": {"cob": 0}},
                },
            ],
            NOW,
        )
        self.assertEqual(data["glucose"], 105)
        self.assertEqual(data["glucose_timestamp"], NOW)
        self.assertEqual(data["trend"], "Flat")
        self.assertEqual(data["iob"], -0.1)
        self.assertEqual(data["cob"], 0)
        self.assertEqual(data["reservoir"], 0)
        self.assertEqual(data["pump_battery"], 35)
        self.assertIs(data["loop_ok"], True)

    def test_stale_values_are_unknown(self):
        data = parse(
            [{"dateString": STALE, "sgv": 110}],
            [{
                "created_at": RECENT,
                "loop": {"timestamp": RECENT, "iob": {"timestamp": STALE, "iob": 1}},
                "pump": {"clock": STALE, "reservoir": 20},
            }],
            NOW,
        )
        self.assertEqual(data["glucose_timestamp"].isoformat(), STALE)
        for key in ("glucose", "iob", "reservoir"):
            self.assertIsNone(data.get(key))

    def test_current_failure_takes_precedence(self):
        data = parse([], [
            {"created_at": RECENT, "loop": {"failureReason": "Synthetic error"}},
            {"created_at": STALE, "loop": {"timestamp": STALE}},
        ], NOW)
        self.assertIs(data["loop_ok"], False)

    def test_missing_and_malformed_fields(self):
        self.assertEqual(parse([], [], NOW), {})
        data = parse(
            [{"dateString": RECENT, "sgv": "NaN"}],
            [{"created_at": RECENT, "pump": {"reservoir": -1, "battery": {"percent": 140}}}],
            NOW,
        )
        self.assertEqual(set(data), {"glucose_timestamp"})

    def test_uploader_battery_and_pump_status(self):
        data = parse([], [{
            "created_at": RECENT,
            "pump": {"model": "Test pump", "suspended": False, "bolusing": True},
            "uploader": {"battery": 73, "timestamp": RECENT},
        }], NOW)
        self.assertEqual(data["pump_model"], "Test pump")
        self.assertIs(data["pump_suspended"], False)
        self.assertIs(data["pump_bolusing"], True)
        self.assertEqual(data["uploader_battery"], 73)
        self.assertNotIn("pump_battery", data)
        self.assertNotIn("reservoir", data)

    def test_stale_uploader_and_nested_pump_status(self):
        data = parse([], [{
            "created_at": RECENT,
            "pump": {"status": {"suspended": True, "bolusing": False}},
            "uploader": {"battery": 73, "timestamp": STALE},
        }], NOW)
        self.assertIs(data["pump_suspended"], True)
        self.assertIs(data["pump_bolusing"], False)
        self.assertNotIn("uploader_battery", data)

    def test_age_uses_latest_matching_past_event(self):
        records = [
            {"eventType": "Sensor Change", "created_at": "2025-12-31T12:00:00Z"},
            {"eventType": "Sensor Start", "created_at": "2026-01-01T09:00:00Z"},
            {"eventType": "Sensor Start", "created_at": "2026-01-01T13:00:00Z"},
            {"eventType": "Note", "created_at": RECENT},
            {"eventType": "Site Change", "created_at": "invalid"},
        ]
        self.assertEqual(event_age_hours(records, ("Sensor Start", "Sensor Change"), NOW), 3)
        self.assertIsNone(event_age_hours(records, ("Site Change",), NOW))
