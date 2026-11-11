const DASHBOARD_TEXT = {
  en: {
    glucose: "Glucose",
    basal: "Basal",
    bolus: "Bolus",
    glucoseChart: "Glucose · last 6 hours",
    missingConnection: "Add a Nightscout Extended connection first.",
    ageUnavailable: "age unavailable",
    sinceReplacement: "since logged replacement",
    replacementDue: "scheduled replacement time has passed",
    replaceIn: "replace in",
    battery: "Uploader battery",
    unknown: "unknown",
    loopUpdate: "Loop update available",
    deliveryPaused: "Insulin delivery paused for",
    durationJoin: "and",
  },
  sv: {
    glucose: "Glukos",
    basal: "Basal",
    bolus: "Bolus",
    glucoseChart: "Glukos · senaste 6 timmarna",
    missingConnection: "Lägg till en Nightscout Extended-anslutning först.",
    ageUnavailable: "ålder saknas",
    sinceReplacement: "sedan loggat byte",
    replacementDue: "planerad bytestid passerad",
    replaceIn: "byte om",
    battery: "Uppladdarens batteri",
    unknown: "okänt",
    loopUpdate: "Loop-uppdatering tillgänglig",
    deliveryPaused: "Insulintillförsel pausad sedan",
    durationJoin: "och",
  },
};

class NightscoutGlucoseChart extends HTMLElement {
  setConfig({ glucose, chart, locale }) {
    this.glucose = glucose;
    this.locale = locale;
    this.chart = document.createElement("apexcharts-card");
    // Give ApexCharts a full-width container before it measures the layout.
    this.style.display = "block";
    this.style.minWidth = "0";
    this.chart.style.display = "block";
    this.chart.style.width = "100%";
    this.chart.setConfig(chart);
    this.chart.style.setProperty("--ha-card-border-width", "0px");
    this.chart.style.setProperty("--ha-card-box-shadow", "none");
    this.chart.style.setProperty("--ha-card-background", "transparent");

    this.heading = document.createElement("div");
    this.heading.style.padding = "16px 16px 0";
    this.value = document.createElement("strong");
    this.value.style.fontSize = "26px";
    this.value.style.lineHeight = "1.3";
    this.heading.append(this.value);
    const card = document.createElement("ha-card");
    card.append(this.heading, this.chart);
    this.replaceChildren(card);
    if (this._hass) this.hass = this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.chart) return;
    this.chart.hass = hass;
    this.updateHeading();
  }

  connectedCallback() {
    this.updateHeading();
    this.timer = setInterval(() => this.updateHeading(), 1000);
    // Lovelace can resize a view without resizing the browser window.
    let previousWidth = 0;
    this.resizeObserver = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width);
      if (width === previousWidth) return;
      previousWidth = width;
      cancelAnimationFrame(this.resizeFrame);
      if (width > 0) {
        this.resizeFrame = requestAnimationFrame(() => {
          window.dispatchEvent(new Event("resize"));
        });
      }
    });
    this.resizeObserver.observe(this);
  }

  disconnectedCallback() {
    clearInterval(this.timer);
    this.resizeObserver?.disconnect();
    cancelAnimationFrame(this.resizeFrame);
  }

  getCardSize() {
    return (this.chart?.getCardSize?.() ?? 4) + 1;
  }

  updateHeading() {
    if (!this.heading) return;
    const attributes = this._hass?.states?.[this.glucose?.entity_id]?.attributes;
    const reading = attributes?.latest_glucose_reading;
    this.heading.hidden = !reading;
    if (!reading) return;

    const { target_band: band, glucose_colors: colors } = this.glucose;
    const mmol = reading.mg_dl / 18.01559;
    const stale = Date.now() - Date.parse(reading.timestamp) > 600000;
    const unit = attributes.unit_of_measurement ?? "mg/dL";
    const arrows = {
      DoubleUp: "↑↑", SingleUp: "↑", FortyFiveUp: "↗", Flat: "→",
      FortyFiveDown: "↘", SingleDown: "↓", DoubleDown: "↓↓",
    };
    const value = (unit === "mmol/L" ? mmol : reading.mg_dl)
      .toLocaleString(this.locale, { maximumFractionDigits: unit === "mmol/L" ? 1 : 0 });
    this.value.textContent = [value, arrows[reading.direction]].filter(Boolean).join(" ");
    this.value.style.color = stale ? "#d32f2f"
      : mmol < (band?.target_low ?? 3.9) ? colors?.color_below ?? "#d87b00"
      : mmol > (band?.target_high ?? 10) ? colors?.color_above ?? "#d87b00"
      : colors?.color_in_range ?? "#20833b";
    this.value.style.textDecoration = stale ? "line-through" : "none";
  }
}

function deviceStatus(entities, text) {
  const rows = [];
  for (const [key, label, hours] of [
    ["sage", "Dexcom G7", 240],
    ["cage", "Omnipod DASH", 72],
  ]) {
    const id = entities.get(key);
    if (!id) continue;
    const model = entities.get(key === "sage" ? "cgm_model" : "pump_model");
    rows.push(`**${label}** · {% set age = states('${id}') | float(none) %}
{% set unit = state_attr('${id}', 'unit_of_measurement') %}
{% set factor = {'s': 1, 'min': 60, 'h': 3600, 'd': 86400}.get(unit) %}
{% if age is none or factor is none %}
${text.ageUnavailable}
${model ? `{% elif states('${model}') | lower != '${label.toLowerCase()}' %}{{ states('${id}') }} {{ unit }} ${text.sinceReplacement}` : ""}
{% else %}
{% set seconds = ${hours} * 3600 - age * factor %}
{% set total = (seconds / 60) | round(0, 'ceil') | int %}
{% if seconds <= 0 %}${text.replacementDue}
{% elif total >= 1440 %}${text.replaceIn} {{ total // 1440 }}d {{ (total % 1440) // 60 }}h
{% else %}${text.replaceIn} {{ total // 60 }}h {{ total % 60 }}min{% endif %}
{% endif %}`.replaceAll("\n", " "));
  }
  const battery = entities.get("uploader_battery");
  if (battery) rows.push(`**${text.battery}** · {% set battery = states('${battery}') | float(none) %}{% if battery is none %}${text.unknown}{% else %}{{ battery | round(0) | int }} %{% endif %}`);
  const suspended = entities.get("pump_suspended");
  const warning = suspended
    ? `{% if is_state('${suspended}', 'on') %}<ha-alert alert-type="error">{% set changed = as_timestamp(states['${suspended}'].last_changed) %}{% set reported = as_timestamp(state_attr('${suspended}', 'first_reported_suspended_at'), changed) %}{% set minutes = [0, ((as_timestamp(now()) - ([changed, reported] | min)) / 60) | int] | max %}<strong>${text.deliveryPaused} {% if minutes > 60 %}{{ minutes // 60 }}h ${text.durationJoin} {{ minutes % 60 }}min{% else %}{{ minutes }}min{% endif %}</strong></ha-alert>{% endif %}\n\n`
    : "";
  const content = rows.join(" &nbsp;│&nbsp; ");
  const update = entities.get("loop_update");
  const notice = update ? (`{% if is_state('${update}', 'on') %} &nbsp;│&nbsp; **${text.loopUpdate}**{% set latest = state_attr('${update}', 'latest_version') %}{% if latest %} · {{ latest }}{% endif %}{% endif %}`) : "";
  if (!rows.length && !update && !suspended) return null;
  return { type: "markdown", content: warning + content + notice, grid_options: { columns: "full" } };
}

class NightscoutDashboard extends HTMLElement {
  static glucoseReadings = new Map();
  static bolusAmounts = new Map();

  static async generate(config, hass) {
    const registry = await hass.callWS({ type: "nightscout_extended/dashboard_entities" });
    const entries = new Map();
    const visible = new Map();
    for (const entity of registry) {
      visible.set(entity.entity_id, entity.graph_visible);
      const prefix = entity.config_entry_id + "_";
      if (!entity.unique_id?.startsWith(prefix)) continue;
      if (!entries.has(entity.config_entry_id)) entries.set(entity.config_entry_id, new Map());
      entries.get(entity.config_entry_id).set(entity.unique_id.slice(prefix.length), entity.entity_id);
    }

    const language = (hass.language || "en").toLowerCase().split("-")[0];
    const text = DASHBOARD_TEXT[language] ?? DASHBOARD_TEXT.en;
    const views = [...entries].map(([id, entities], index) => {
      const glucose = entities.get("glucose");
      const sections = [];
      const apex = customElements.get("apexcharts-card");
      const graphs = [];
      const basalEntity = entities.get("temporary_basal");
      const basal = basalEntity ? [{
        entity: basalEntity, name: text.basal, color: "#00897b", yaxis_id: "basal",
        curve: "stepline", extend_to: false, stroke_width: 2,
        show: { hidden_by_default: !(visible.get(basalEntity) ?? false), legend_value: false },
        data_generator: "return entity.attributes.combined_basal_history || [];",
      }] : [];
      const glucoseEntity = registry.find(entity => entity.entity_id === glucose);
      const band = glucoseEntity?.target_band;
      const bounds = glucoseEntity?.glucose_axis;
      const unit = hass.states?.[glucose]?.attributes.unit_of_measurement;
      const factor = unit === "mg/dL" ? 18.01559 : 1;
      const axis = bounds && ["mmol/L", "mg/dL"].includes(unit)
        ? { min: bounds.axis_low * factor, max: bounds.axis_high * factor }
        : {};
      const series = glucose ? [{
        entity: glucose, name: text.glucose, yaxis_id: "glucose",
        data_generator: `
          const points = entity.attributes.glucose_history_mg_dl || [];
          const divisor = entity.attributes.unit_of_measurement === "mmol/L" ? 18.01559 : 1;
          const min = ${JSON.stringify(axis.min ?? null)};
          const max = ${JSON.stringify(axis.max ?? null)};
          customElements.get("ll-strategy-dashboard-nightscout-extended")
            .glucoseReadings.set(entity.entity_id, new Map(points.map(([time, value]) => [time, value / divisor])));
          return points.map(([time, glucose]) => [
            time, Math.min(max ?? Infinity, Math.max(min ?? -Infinity, glucose / divisor)),
          ]);
        `,
        show: { hidden_by_default: !(visible.get(glucose) ?? true), legend_value: false },
        color: "#2674d9", curve: "straight", stroke_width: 2, extend_to: false,
      }, {
        entity: glucose, name: text.bolus, yaxis_id: "glucose",
        color: "#ad3e87", stroke_width: 0, extend_to: false,
        show: {
          legend_value: false,
          in_header: false,
          hidden_by_default: !(glucoseEntity?.bolus_visible ?? true),
        },
        data_generator: `
          const glucose = entity.attributes.glucose_history_mg_dl || [];
          const amounts = new Map();
          const points = [];
          for (const [time, amount] of entity.attributes.bolus_history || []) {
            let nearest;
            for (const reading of glucose) {
              if (!nearest || Math.abs(reading[0] - time) < Math.abs(nearest[0] - time)) {
                nearest = reading;
              }
            }
            if (!nearest || Math.abs(nearest[0] - time) > 600000) continue;
            const divisor = entity.attributes.unit_of_measurement === "mmol/L" ? 18.01559 : 1;
            const y = Math.min(${JSON.stringify(axis.max ?? null)} ?? Infinity,
              Math.max(${JSON.stringify(axis.min ?? null)} ?? -Infinity, nearest[1] / divisor));
            points.push([time, y]);
            amounts.set(time, [...(amounts.get(time) || []), amount]);
          }
          customElements.get("ll-strategy-dashboard-nightscout-extended")
            .bolusAmounts.set(entity.entity_id, amounts);
          return points;
        `,
      }, ...basal] : basal;
      const showBand = band?.target_band && ["mmol/L", "mg/dL"].includes(unit)
        && Number.isFinite(band.target_low) && Number.isFinite(band.target_high)
        && band.target_low < band.target_high;
      const low = showBand ? band.target_low * factor : null;
      const high = showBand ? band.target_high * factor : null;
      if (apex && series.length) graphs.push({
        type: "custom:apexcharts-card", graph_span: "6h",
        header: { show: false },
        experimental: { hidden_by_default: true },
        apex_config: {
          chart: { height: 340, redrawOnWindowResize: true },
          ...(showBand ? { annotations: {
            position: "back",
            yaxis: [{ y: low, y2: high, yAxisIndex: 0,
              fillColor: "#66bb6a", borderColor: "transparent", opacity: 0.19 }],
          } } : {}),
          markers: { size: series.map(item => item.name === text.bolus ? 6 : item.yaxis_id === "glucose" ? 4 : 0) },
          tooltip: {
            intersect: false, shared: false, x: { format: "dd MMM HH:mm:ss" },
            ...(glucose ? { y: { formatter: `EVAL:(value, { seriesIndex, dataPointIndex, w }) => {
              if (seriesIndex !== 0 && seriesIndex !== 1) return value;
              const time = w.globals.seriesX[seriesIndex]?.[dataPointIndex];
              const dashboard = customElements.get("ll-strategy-dashboard-nightscout-extended");
              const locale = ${JSON.stringify(text === DASHBOARD_TEXT.sv ? "sv" : "en")};
              if (seriesIndex === 1) {
                const amounts = dashboard.bolusAmounts.get(${JSON.stringify(glucose)})?.get(time) || [];
                return amounts.map(amount => amount.toLocaleString(locale, { maximumFractionDigits: 3 }) + " U").join(", ");
              }
              const measured = dashboard.glucoseReadings.get(${JSON.stringify(glucose)})?.get(time);
              return Number(measured ?? value).toLocaleString(locale, { maximumFractionDigits: 1 })
                + " " + ${JSON.stringify(unit ?? "")};
            }` } } : {}),
          },
        },
        yaxis: [
          {
            id: "glucose", ...axis,
            apex_config: {
              title: { text: text.glucose },
              tickAmount: bounds && Number.isFinite(axis.min) && Number.isFinite(axis.max)
                ? Math.max(1, Math.floor((bounds.axis_high - bounds.axis_low) / 2))
                : 5,
            },
          },
          { id: "basal", min: 0, max: "~4", opposite: true, apex_config: { title: { text: "Basal (U/h)" } } },
        ].filter(axis => series.some(item => item.yaxis_id === axis.id)),
        series,
        grid_options: { columns: "full" },
      });
      if (graphs.length) sections.unshift({
        type: "grid",
        column_span: 2,
        cards: graphs.map(chart => ({
          type: "custom:nightscout-extended-glucose-chart",
          chart,
          glucose: glucoseEntity,
          locale: language === "sv" ? "sv" : "en",
          grid_options: { columns: "full" },
        })),
      });
      if (glucose && !apex) sections.unshift({
        type: "grid",
        column_span: 2,
        cards: [{
          type: "history-graph",
          title: text.glucoseChart,
          hours_to_show: 6,
          entities: [glucose],
          grid_options: { columns: "full" },
        }],
      });
      const status = deviceStatus(entities, text);
      if (status) sections.unshift({ type: "grid", column_span: 2, cards: [status] });
      return { type: "sections", max_columns: 2, path: id,
        title: registry.find(entity => entity.config_entry_id === id)?.dashboard_tab_name
          || hass.devices?.[registry.find(entity => entity.entity_id === glucose)?.device_id]?.name
          || "Nightscout " + (index + 1), sections };
    });
    return { views: views.length ? views : [{
      title: "Nightscout",
      cards: [{ type: "markdown", content: text.missingConnection }],
    }] };
  }
}

const chartTag = "nightscout-extended-glucose-chart";
if (!customElements.get(chartTag)) customElements.define(chartTag, NightscoutGlucoseChart);

const tag = "ll-strategy-dashboard-nightscout-extended";
if (!customElements.get(tag)) {
  customElements.define(tag, NightscoutDashboard);
  window.customStrategies ??= [];
  window.customStrategies.push({
    type: "nightscout-extended",
    strategyType: "dashboard",
    name: "Nightscout Extended",
    description: "Dashboard with automatically selected Nightscout entities.",
  });
}
