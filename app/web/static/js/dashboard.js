const API = "";

document.getElementById("apiHost").textContent = window.location.origin;

const cardsEl = document.getElementById("cards");
const sensorSelect = document.getElementById("sensorSelect");
const limitInput = document.getElementById("limitInput");
const loadBtn = document.getElementById("loadBtn");
const autoBtn = document.getElementById("autoBtn");
const lastRefresh = document.getElementById("lastRefresh");
const errorBox = document.getElementById("errorBox");
const alertSummaryEl = document.getElementById("alertSummary");
const alertListEl = document.getElementById("alertList");

const offlineMinEl = document.getElementById("offlineMin");
const batteryLowEl = document.getElementById("batteryLow");
const humidityWarnEl = document.getElementById("humidityWarn");
const tempHighEl = document.getElementById("tempHigh");

let autoRefresh = true;
let chart = null;

const fmtTs = (ts) => (ts ? new Date(ts * 1000).toLocaleString() : "-");
const num = (v, d = 2) => (v === null || v === undefined ? "-" : Number(v).toFixed(d));

function params() {
  return new URLSearchParams({
    offline_min: String(Number(offlineMinEl.value || 15)),
    battery_low_mv: String(Number(batteryLowEl.value || 2600)),
    humidity_warn_pct: String(Number(humidityWarnEl.value || 70)),
    temp_high_c: String(Number(tempHighEl.value || 28)),
  }).toString();
}

function minutesSince(ts) {
  if (!ts) return Number.POSITIVE_INFINITY;
  return (Date.now() / 1000 - ts) / 60;
}

function classifySensor(s) {
  const offlineMin = Number(offlineMinEl.value || 15);
  const batteryLow = Number(batteryLowEl.value || 2600);
  const humWarn = Number(humidityWarnEl.value || 70);
  const tempHigh = Number(tempHighEl.value || 28);

  const age = minutesSince(s.ts);
  const offline = age > offlineMin;
  const battLow = (s.battery_mv ?? 99999) < batteryLow;
  const humHigh = (s.humidity_pct ?? 0) >= humWarn;
  const tHigh = (s.temperature_c ?? -999) >= tempHigh;

  let level = "ok";
  if (offline || battLow || humHigh || tHigh) level = "warn";
  if (offline && battLow) level = "danger";
  return { level, age, offline, battLow, humHigh, tHigh };
}

async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}

function renderCards(items) {
  cardsEl.innerHTML = "";
  for (const s of items) {
    const c = classifySensor(s);
    const badges = [
      `<span class="badge ${c.level === "ok" ? "ok" : c.level === "danger" ? "danger" : "warn"}">${c.level.toUpperCase()}</span>`,
    ];
    if (c.offline) badges.push('<span class="badge danger">OFFLINE</span>');
    if (c.battLow) badges.push('<span class="badge warn">LOW BATTERY</span>');
    if (c.humHigh) badges.push('<span class="badge warn">HUM HIGH</span>');
    if (c.tHigh) badges.push('<span class="badge warn">TEMP HIGH</span>');

    const div = document.createElement("div");
    div.className = `card ${c.level}`;
    div.innerHTML = `
      <div class="sensor-title">
        <span>${s.sensor_id}</span>
        <span class="badges">${badges.join("")}</span>
      </div>
      <div class="kv"><b>Name:</b> ${s.name || "-"}</div>
      <div class="kv"><b>Last seen:</b> ${fmtTs(s.ts)} (${num(c.age, 1)} min ago)</div>
      <div class="kv"><b>Temperature:</b> ${num(s.temperature_c, 3)} deg C</div>
      <div class="kv"><b>Humidity:</b> ${num(s.humidity_pct, 3)} %</div>
      <div class="kv"><b>Pressure:</b> ${num(s.pressure_pa, 1)} Pa</div>
      <div class="kv"><b>Battery:</b> ${s.battery_mv ?? "-"} mV</div>
      <div class="kv"><b>RSSI:</b> ${s.rssi ?? "-"} dBm</div>
      <div class="kv"><b>Movement:</b> ${s.movement_counter ?? "-"}</div>
    `;
    cardsEl.appendChild(div);
  }
}

function ensureChart() {
  if (chart) return chart;
  chart = new Chart(document.getElementById("historyChart").getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Temperature deg C",
          data: [],
          borderColor: "#e67e22",
          backgroundColor: "rgba(230,126,34,.15)",
          tension: 0.2,
          yAxisID: "y",
        },
        {
          label: "Humidity %",
          data: [],
          borderColor: "#c0392b",
          backgroundColor: "rgba(192,57,43,.12)",
          tension: 0.2,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { type: "linear", position: "left", title: { display: true, text: "deg C" } },
        y1: {
          type: "linear",
          position: "right",
          title: { display: true, text: "%" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
  return chart;
}

async function loadHistory() {
  const sid = sensorSelect.value;
  if (!sid) return;
  const limit = Math.max(10, Math.min(2000, Number(limitInput.value || 200)));
  const data = await fetchJson(`${API}/history?sensor_id=${encodeURIComponent(sid)}&limit=${limit}`);
  const items = (data.items || []).slice().reverse();

  const c = ensureChart();
  c.data.labels = items.map((i) => fmtTs(i.ts));
  c.data.datasets[0].data = items.map((i) => i.temperature_c);
  c.data.datasets[1].data = items.map((i) => i.humidity_pct);
  c.update();
}

function renderAlertSummary(summary) {
  const danger = summary.by_severity?.danger || 0;
  const warn = summary.by_severity?.warn || 0;
  const total = summary.count_total || 0;

  alertSummaryEl.innerHTML = `
    <span class="pill ${danger > 0 ? "danger" : "ok"}">Danger: ${danger}</span>
    <span class="pill ${warn > 0 ? "warn" : "ok"}">Warn: ${warn}</span>
    <span class="pill ${total > 0 ? "warn" : "ok"}">Total alerts: ${total}</span>
  `;
}

function renderAlerts(items) {
  alertListEl.innerHTML = "";
  if (!items.length) {
    alertListEl.innerHTML = '<div class="muted">No active alerts.</div>';
    return;
  }

  for (const a of items) {
    const div = document.createElement("div");
    div.className = `alert-item ${a.severity}`;
    div.innerHTML = `
      <div><b>${a.sensor_id}</b> <span class="muted">(${a.type})</span></div>
      <div>${a.message}</div>
      <div class="muted">Last sample: ${fmtTs(a.ts)} | RSSI: ${a.rssi ?? "-"} dBm</div>
    `;
    alertListEl.appendChild(div);
  }
}

async function refreshAll() {
  try {
    errorBox.textContent = "";
    const latest = await fetchJson(`${API}/latest`);
    const latestItems = latest.items || [];
    renderCards(latestItems);

    const ids = latestItems.map((x) => x.sensor_id);
    const current = sensorSelect.value;
    sensorSelect.innerHTML = ids.map((id) => `<option value="${id}">${id}</option>`).join("");
    if (ids.includes(current)) sensorSelect.value = current;

    await loadHistory();

    const summary = await fetchJson(`${API}/alert-summary?${params()}`);
    renderAlertSummary(summary);

    const alerts = await fetchJson(`${API}/alerts?${params()}`);
    renderAlerts(alerts.items || []);

    lastRefresh.textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
  } catch (e) {
    console.error(e);
    errorBox.textContent = `Refresh error: ${e.message}`;
  }
}

loadBtn.addEventListener("click", loadHistory);
autoBtn.addEventListener("click", () => {
  autoRefresh = !autoRefresh;
  autoBtn.textContent = `Auto refresh: ${autoRefresh ? "ON" : "OFF"}`;
});

[offlineMinEl, batteryLowEl, humidityWarnEl, tempHighEl].forEach((el) => {
  el.addEventListener("change", refreshAll);
});

refreshAll();
setInterval(() => {
  if (autoRefresh) refreshAll();
}, 5000);
