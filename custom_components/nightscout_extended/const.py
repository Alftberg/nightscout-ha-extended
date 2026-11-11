"""Integration constants."""

DOMAIN = "nightscout_extended"

AGE_EVENTS = {
    "cage": ("Site Change",),
    "iage": ("Insulin Change",),
    "bage": ("Pump Battery Change",),
    "sage": ("Sensor Start", "Sensor Change"),
}

GLUCOSE_SENSOR_KEYS = ("glucose", "glucose_forecast", "glucose_delta")
GLUCOSE_UNITS = ("mmol/L", "mg/dL")

TREND_STATES = {
    "DoubleUp": "double_up",
    "SingleUp": "single_up",
    "FortyFiveUp": "forty_five_up",
    "Flat": "flat",
    "FortyFiveDown": "forty_five_down",
    "SingleDown": "single_down",
    "DoubleDown": "double_down",
    "NONE": "no_trend",
    "NOT COMPUTABLE": "not_computable",
    "RATE OUT OF RANGE": "rate_out_of_range",
}

OVERRIDE_EVENTS = ("Temporary Override", "Temporary Override Cancel")


GRAPH_DEFAULTS = {
    "glucose": True,
    "bolus": True,
    "temporary_basal": False,
}

GLUCOSE_COLOR_DEFAULTS = {"color_below": "#d87b00", "color_in_range": "#20833b", "color_above": "#d87b00"}
TARGET_BAND_DEFAULTS = {"target_band": True, "target_low": 3.9, "target_high": 10.0}

GLUCOSE_AXIS_DEFAULTS = {"axis_low": 2, "axis_high": 16}
