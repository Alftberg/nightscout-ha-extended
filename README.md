# Nightscout Extended

Nightscout Extended reads glucose and Loop telemetry from Nightscout API v1 into Home Assistant. It polls once a minute and requires Home Assistant 2026.1.0 or later.

Please understand that this project:

- Is highly experimental
- Is not approved for therapy

## Entities

| Entity | Source |
| --- | --- |
| Glucose, change, trend and measurement time | `entries/sgv` |
| Insulin on board (IOB), carbs on board (COB), Loop result, report time, version and glucose forecast | `devicestatus.loop` |
| Pump model, delivery status, bolus status, reservoir and pump battery | `devicestatus.pump` |
| Pump status time | `devicestatus.pump.clock` or the report timestamp |
| Uploader battery and charging status | `devicestatus.uploader` |
| Loop override status | `devicestatus.override.active` |
| Active temporary profile | Loop status and `Temporary Override` in `treatments` |
| Infusion site age (CAGE) | Latest `Site Change` in `treatments` |
| Glucose sensor age (SAGE) | Latest `Sensor Start` or `Sensor Change` in `treatments` |
| Time since insulin change (IAGE) | Latest `Insulin Change` in `treatments` |
| Time since pump battery change (BAGE) | Latest `Pump Battery Change` in `treatments` |

The active temporary profile uses the name reported by Loop, with the logged override as a fallback. When an ongoing event can be matched, the entity exposes the start time and any end time. It also exposes `insulin_scale_percent`, `target_min_mg_dl` and `target_max_mg_dl` when available. A zero-duration override has no fixed end time.

The glucose forecast shows the last valid forecast point. Its `forecast_points` attribute contains timestamps and values in mg/dL regardless of the display unit. Glucose change compares the two most recent valid, fresh readings with distinct timestamps. The text trend follows the Home Assistant language.

Age sensors report hours since the corresponding event and show as unknown if the event is missing or `treatments` is inaccessible. Missing or stale readings older than 15 minutes show as unknown. The latest glucose timestamp can still be shown. Connection failures make entities unavailable.

Glucose arrives in mg/dL. New connections display mmol/L by default. Change the unit for glucose, glucose change and forecast under **Settings → Devices & services → Nightscout Extended → Configure**. The integration fetches six hours of glucose history once per connection and stores it locally. Subsequent updates fetch only the five latest glucose records.

## Install via HACS

1. Open **HACS → ⋮ → Custom repositories**.
2. Add [Alftberg/nightscout-ha-extended](https://github.com/Alftberg/nightscout-ha-extended) as an **Integration**.
3. Download **Nightscout Extended** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Nightscout Extended**.
5. Enter the Nightscout URL, for example `https://nightscout.example.org`. Supply a token with read access if your server requires one. Use HTTPS for remote connections.

The diagnostics file contains only the status of the latest fetch. Configure the URL and token in Home Assistant. Tests use synthetic data.

## Dashboard

1. Reload the browser after restarting Home Assistant. The integration registers the dashboard module automatically when Lovelace resources are managed through the UI.
2. Create a dashboard and paste the following into its raw configuration editor.

```yaml
strategy:
  type: custom:nightscout-extended
```

When editing the strategy itself, enter only `type: custom:nightscout-extended`.

Each Nightscout connection gets its own view with a status summary and glucose history. With ApexCharts Card loaded, the combined chart shows individual glucose readings. Use the legend to toggle bolus markers and basal. The header shows sensor and pod replacement countdowns, uploader battery and any available Loop update. The dashboard falls back to Home Assistant's built-in glucose chart if ApexCharts Card is unavailable.

For YAML-managed resources, add the module to the existing `lovelace.resources` list in `configuration.yaml`.

```yaml
lovelace:
  resources:
    - url: /nightscout_extended/dashboard.js?v=0.1.29
      type: module
```

### ApexCharts dashboard example

The example shows six hours of glucose readings, basal rates and insulin on board, with cards for CAGE, SAGE and replacement countdowns.

1. Install [ApexCharts Card](https://github.com/RomRider/apexcharts-card#installation) through HACS.
2. Copy the [dashboard example](dashboards/nightscout-example.yaml) and substitute your own entity IDs. List them in Home Assistant's template editor with `{{ integration_entities('nightscout_extended') | sort | join('\n') }}`.
3. Create a separate dashboard, open **Edit dashboard → ⋮ → Raw configuration editor**, paste the example and save.

Calculated basal requires Nightscout Extended v0.1.12 or later. It shows the logged temporary rate during each active interval, including 0 U/h, and the saved default profile's schedule between intervals. The dashed line shows scheduled basal. Historical profile changes can cause differences from Nightscout. The example plots glucose and insulin on board from Home Assistant history.

Countdowns use three days for Omnipod DASH and ten days for Dexcom G7. Edit the model names and time limits in the example for other devices.

## Treatment and profile entities

- **Calculated trend rate** divides the glucose change by the time between readings and uses the configured glucose unit per minute.
- **Logged temporary basal** shows the most recent active `Temp Basal` rate and becomes unknown when the interval ends.
- **Latest carb correction** and **Latest correction bolus** show the last logged amount for each event, with timestamps and available metadata as attributes.
- **Saved default profile** and **Scheduled basal** come from `profile`. The scheduled rate uses the profile's time zone.

## Loop updates

The **Loop update** entity compares the reported version with the latest stable [LoopWorkspace release](https://github.com/LoopKit/LoopWorkspace/releases). When Nightscout reports a valid Loop version, the integration checks GitHub at startup or when Loop is first detected, then approximately every six hours. Home Assistant posts a notification for each newer release with a link to the release notes. The comparison ignores the build number. Install updates through your usual Loop build process.

## Local checks

```sh
python3 -m compileall -q custom_components
python3 -m unittest discover -s tests -v
```
