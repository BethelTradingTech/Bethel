(function () {
  "use strict";

  const API = "https://api.betheltradingtechnologies.com";
  const performanceSection = document.getElementById("performance");
  const broadcastSection = document.getElementById("public-broadcast");
  const liveSection = document.getElementById("public-live-mt5");
  if (!performanceSection) return;

  let loading = false;

  const style = document.createElement("style");
  style.textContent = `
    #public-broadcast,#public-live-mt5{display:none!important;padding:0!important;margin:0!important;height:0!important;min-height:0!important;overflow:hidden!important}
    .unified-live-title{text-align:center;margin-bottom:1rem}
    .unified-live-title h2{font-size:2.25rem;margin-bottom:.5rem}
    .unified-live-title p{color:var(--text-secondary);max-width:760px;margin:0 auto}
    .unified-live-panel{background:var(--card-bg);border:2px solid rgba(16,185,129,.5);border-radius:18px;padding:1.25rem;display:grid;gap:1rem;box-shadow:0 0 28px rgba(16,185,129,.10)}
    .returns-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}
    .returns-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-table-wrap{width:100%;max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;-webkit-overflow-scrolling:touch}
    .track-table{width:100%;border-collapse:collapse;min-width:1050px;font-size:.8rem}
    .track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}
    .track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}
    .track-table th:last-child,.track-table td:last-child{font-weight:800}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}
    .track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    .unified-live-panel .public-broadcast-shell,.unified-live-panel .live-mt5-shell{max-width:none;margin:0;width:100%}
    .unified-live-panel .public-broadcast-shell{border:1px solid rgba(16,185,129,.35);box-shadow:none}
    .unified-live-panel .live-mt5-shell{padding:1rem}
    #broadcast-slot[hidden],#telemetry-slot[hidden]{display:none!important}
    @media(max-width:600px){.unified-live-title h2{font-size:1.35rem}.unified-live-title p{font-size:.8rem}.unified-live-panel{padding:.6rem;border-width:1px}.returns-panel{padding:.6rem}.track-table{font-size:.72rem;min-width:900px}.track-table th,.track-table td{padding:.45rem .5rem}}
  `;
  document.head.appendChild(style);

  const fmtSignedPercent = (value, digits = 2) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`;
  };

  const fmtDate = (value) => {
    if (!value) return "—";
    const raw = String(value);
    const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw) ? `${raw}T00:00:00Z` : raw);
    return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  };

  function buildUnifiedDisplay() {
    const broadcastShell = broadcastSection ? broadcastSection.querySelector(".public-broadcast-shell") : null;
    const liveShell = liveSection ? liveSection.querySelector(".live-mt5-shell") : null;

    performanceSection.innerHTML = `
      <div class="unified-live-title">
        <h2>LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1</h2>
        <p>Live read-only Bethel Terminal 1 broadcast and account telemetry, followed by the active master's monthly and yearly return record.</p>
      </div>
      <div id="unified-live-panel" class="unified-live-panel">
        <div id="broadcast-slot" hidden></div>
        <div id="telemetry-slot" hidden></div>
        <div class="returns-panel">
          <h3>Monthly & Yearly Returns</h3>
          <div id="track-loading" class="track-loading">Loading return history…</div>
          <div id="track-monthly" class="track-table-wrap" hidden></div>
        </div>
      </div>`;

    const broadcastSlot = document.getElementById("broadcast-slot");
    const telemetrySlot = document.getElementById("telemetry-slot");
    if (broadcastShell && broadcastSlot) broadcastSlot.appendChild(broadcastShell);
    if (liveShell && telemetrySlot) telemetrySlot.appendChild(liveShell);

    if (broadcastSection && broadcastSection.isConnected) broadcastSection.remove();
    if (liveSection && liveSection.isConnected) liveSection.remove();
  }

  function renderMonthly(rows, historyStart, historyEnd) {
    const container = document.getElementById("track-monthly");
    if (!container) return;

    const startPeriod = /^\d{4}-\d{2}/.test(String(historyStart || "")) ? String(historyStart).slice(0,7) : null;
    const endPeriod = /^\d{4}-\d{2}/.test(String(historyEnd || "")) ? String(historyEnd).slice(0,7) : null;
    const valid = (Array.isArray(rows) ? rows : [])
      .filter(r => /^\d{4}-\d{2}$/.test(String(r.period || "")) && Number.isFinite(Number(r.return_percent)))
      .filter(r => (!startPeriod || r.period >= startPeriod) && (!endPeriod || r.period <= endPeriod))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)));

    if (!valid.length) {
      container.innerHTML = '<span class="track-history-label">Monthly return history is not yet available for the active master.</span>';
      container.hidden = false;
      return;
    }

    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const years = [...new Set(valid.map(r => String(r.period).slice(0,4)))].sort();
    const byMonth = new Map(valid.map(r => [String(r.period), Number(r.return_percent)]));

    const table = document.createElement("table");
    table.className = "track-table";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Year", ...months, "Year"].forEach(label => {
      const th = document.createElement("th");
      th.textContent = label;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    years.forEach(year => {
      const tr = document.createElement("tr");
      const yearCell = document.createElement("td");
      yearCell.textContent = year;
      tr.appendChild(yearCell);

      const yearValues = [];
      for (let month = 1; month <= 12; month += 1) {
        const key = `${year}-${String(month).padStart(2,"0")}`;
        const value = byMonth.get(key);
        const td = document.createElement("td");
        if (Number.isFinite(value)) {
          td.textContent = fmtSignedPercent(value);
          td.className = value > 0 ? "track-positive" : value < 0 ? "track-negative" : "track-neutral";
          yearValues.push(value / 100);
        } else {
          td.textContent = "—";
          td.className = "track-neutral";
        }
        tr.appendChild(td);
      }

      const annual = yearValues.length ? (yearValues.reduce((factor,r)=>factor*(1+r),1)-1)*100 : NaN;
      const total = document.createElement("td");
      total.textContent = Number.isFinite(annual) ? fmtSignedPercent(annual) : "—";
      total.className = annual > 0 ? "track-positive" : annual < 0 ? "track-negative" : "track-neutral";
      tr.appendChild(total);
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.innerHTML = "";
    container.appendChild(table);

    const note = document.createElement("div");
    note.className = "track-history-label";
    note.style.marginTop = ".65rem";
    note.textContent = `Active-master returns · ${fmtDate(historyStart)} — ${fmtDate(historyEnd)}.`;
    container.appendChild(note);
    container.hidden = false;
  }

  async function fetchSummary() {
    const response = await fetch(`${API}/performance/public-summary?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}});
    if (!response.ok) throw new Error("summary unavailable");
    const data = await response.json();
    if (!data.available) throw new Error("return history unavailable");
    return data;
  }

  async function syncPublicVisibility() {
    const broadcastSlot = document.getElementById("broadcast-slot");
    const telemetrySlot = document.getElementById("telemetry-slot");
    try {
      const [broadcastResponse, telemetryResponse] = await Promise.all([
        fetch(`${API}/broadcast/v1/public/status?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}}),
        fetch(`${API}/connector/v1/public/live?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}})
      ]);
      const broadcast = broadcastResponse.ok ? await broadcastResponse.json() : null;
      const telemetry = telemetryResponse.ok ? await telemetryResponse.json() : null;
      if (broadcastSlot) broadcastSlot.hidden = !(broadcast && broadcast.enabled && broadcast.hls_url);
      if (telemetrySlot) telemetrySlot.hidden = !(telemetry && telemetry.enabled);
    } catch (_) {
      if (broadcastSlot) broadcastSlot.hidden = true;
      if (telemetrySlot) telemetrySlot.hidden = true;
    }
  }

  async function loadReturns() {
    if (loading) return;
    loading = true;
    try {
      const data = await fetchSummary();
      const summaryAgain = await fetchSummary();
      if (summaryAgain.account_number !== data.account_number) {
        throw new Error("active master changed during refresh");
      }
      renderMonthly(data.monthly_returns || [], data.history_start, data.history_end);
      const loadingEl = document.getElementById("track-loading");
      if (loadingEl) loadingEl.hidden = true;
    } catch (_) {
      const loadingEl = document.getElementById("track-loading");
      if (loadingEl) {
        loadingEl.className = "track-error";
        loadingEl.hidden = false;
        loadingEl.textContent = "Monthly and yearly returns are temporarily unavailable while the active master record is refreshing.";
      }
    } finally {
      loading = false;
    }
  }

  buildUnifiedDisplay();
  syncPublicVisibility();
  loadReturns();
  setInterval(syncPublicVisibility, 5000);
  setInterval(loadReturns, 15000);
})();
