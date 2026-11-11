"""Integration constants."""

DOMAIN = "nightscout_extended"

AGE_EVENTS = {
    "cage": ("Site Change",),
    "iage": ("Insulin Change",),
    "bage": ("Pump Battery Change",),
    "sage": ("Sensor Start", "Sensor Change"),
}

GLUCOSE_SENSOR_KEYS = ("glucose", "glucose_forecast")
GLUCOSE_UNITS = ("mmol/L", "mg/dL")
