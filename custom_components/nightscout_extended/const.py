"""Integration constants."""

DOMAIN = "nightscout_extended"

AGE_EVENTS = {
    "cage": ("Site Change",),
    "iage": ("Insulin Change",),
    "bage": ("Pump Battery Change",),
    "sage": ("Sensor Start", "Sensor Change"),
}
