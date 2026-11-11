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
