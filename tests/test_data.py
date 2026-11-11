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
        self.assertEqual(set(data), {"glucose_timestamp", "pump_timestamp"})

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

    def test_fresh_status_and_forecast(self):
        data = parse([], [{
            "created_at": RECENT,
            "pump": {"clock": RECENT},
            "uploader": {"isCharging": False},
            "override": {"active": True},
            "loop": {
                "timestamp": RECENT,
                "version": "1.2.3",
                "predicted": {"startDate": RECENT, "values": [100, None, 112]},
            },
        }], NOW)
        self.assertEqual(data["pump_timestamp"].isoformat(), RECENT)
        self.assertIs(data["uploader_charging"], False)
        self.assertIs(data["override_active"], True)
        self.assertEqual(data["loop_version"], "1.2.3")
        self.assertEqual(data["glucose_forecast"], 112)
        self.assertEqual(data["forecast_points"], [
            {"timestamp": RECENT, "mg_dl": 100},
            {"timestamp": (NOW + timedelta(minutes=8)).isoformat(), "mg_dl": 112},
        ])

    def test_stale_override_and_prediction_are_unknown(self):
        data = parse([], [{
            "created_at": RECENT,
            "override": {"active": True, "timestamp": STALE},
            "loop": {
                "timestamp": RECENT,
                "predicted": {"startDate": STALE, "values": [100, 112]},
            },
        }], NOW)
        self.assertNotIn("override_active", data)
        self.assertNotIn("glucose_forecast", data)

    def test_glucose_delta_skips_duplicate_timestamp(self):
        data = parse([
            {"dateString": NOW.isoformat(), "sgv": 100},
            {"dateString": NOW.isoformat(), "sgv": 102},
            {"dateString": RECENT, "sgv": 104},
        ], [], NOW)
        self.assertEqual(data["glucose_delta"], -4)

    def test_glucose_delta_requires_two_fresh_readings(self):
        data = parse([
            {"dateString": NOW.isoformat(), "sgv": 100},
            {"dateString": STALE, "sgv": 104},
        ], [], NOW)
        self.assertNotIn("glucose_delta", data)

    def test_active_override_without_fixed_end(self):
        name, attributes = parser["active_override_profile"]([
            {"eventType": "Temporary Override", "created_at": RECENT,
             "reason": "exercise", "reasonDisplay": "Exercise", "duration": 0},
        ], NOW)
        self.assertEqual(name, "Exercise")
        self.assertEqual(attributes, {"started_at": RECENT})

    def test_cancelled_and_expired_overrides(self):
        profile = parser["active_override_profile"]
        started = {"eventType": "Temporary Override", "created_at": RECENT,
                   "reason": "exercise", "duration": 1}
        self.assertEqual(profile([started], NOW), (None, {}))
        started["duration"] = 10
        self.assertEqual(profile([started], NOW)[0], "exercise")
        cancel = {"eventType": "Temporary Override Cancel", "created_at": RECENT}
        self.assertEqual(profile([cancel, started], NOW), (None, {}))

    def test_override_status_attributes(self):
        data = parse([], [{
            "created_at": RECENT,
            "override": {"active": True, "multiplier": 0.5,
                         "currentCorrectionRange": {"minValue": 100, "maxValue": 110}},
        }], NOW)
        self.assertEqual(data["override_attributes"], {
            "insulin_scale_percent": 50,
            "target_min_mg_dl": 100,
            "target_max_mg_dl": 110,
        })

    def test_treatment_snapshot(self):
        snapshot = parser["treatment_snapshot"]
        basal = {"eventType": "Temp Basal", "created_at": RECENT,
                 "duration": 5, "absolute": 0}
        carb = {"eventType": "Carb Correction", "created_at": STALE,
                "carbs": 10, "absorptionTime": 60}
        bolus = {"eventType": "Correction Bolus", "created_at": RECENT,
                 "insulin": 1, "automatic": False}
        data = snapshot([basal, carb, bolus], NOW)
        self.assertEqual(data["temporary_basal"], 0)
        self.assertEqual(data["last_carbs_details"]["absorption_minutes"], 60)
        self.assertIs(data["last_correction_bolus_details"]["automatic"], False)
        self.assertNotIn("temporary_basal", snapshot([basal], NOW + timedelta(minutes=4)))

    def test_saved_profile_uses_local_schedule(self):
        profile = {
            "defaultProfile": "Synthetic",
            "store": {"Synthetic": {"timezone": "Europe/Stockholm", "basal": [
                {"timeAsSeconds": 0, "value": 0.5},
                {"timeAsSeconds": 13 * 3600, "value": 0.8},
            ]}},
        }
        data = parser["saved_profile"]([profile], NOW)
        self.assertEqual(data, {"saved_profile": "Synthetic", "scheduled_basal": 0.8})


    def test_saved_profile_accepts_uppercase_etc_timezone(self):
        profile = {
            "defaultProfile": "Synthetic",
            "store": {"Synthetic": {"timezone": "ETC/GMT-1", "basal": [
                {"timeAsSeconds": 0, "value": 0.5},
                {"timeAsSeconds": 13 * 3600, "value": 0.8},
            ]}},
        }
        self.assertEqual(parser["saved_profile"]([profile], NOW)["scheduled_basal"], 0.8)
