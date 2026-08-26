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
    .unified-live-shell{display:grid;gap:1.1rem}
    .unified-live-title{text-align:center;margin-bottom:1rem}
    .unified-live-title h2{font-size:2.25rem;margin-bottom:.5rem}
    .unified-live-title p{color:var(--text-secondary);max-width:760px;margin:0 auto}
    .unified-live-panel{background:var(--card-bg);border:2px solid rgba(16,185,129,.5);border-radius:18px;padding:1.25rem;display:grid;gap:1rem;box-shadow:0 0 28px rgba(16,185,129,.10)}
    .track-topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}
    .track-verified{display:inline-flex;align-items:center;gap:.5rem;border:1px solid rgba(16,185,129,.35);background:rgba(16,185,129,.08);color:#a7f3d0;border-radius:999px;padding:.5rem .8rem;font-weight:800;font-size:.78rem;letter-spacing:.05em}
    .track-dot{width:.55rem;height:.55rem;border-radius:50%;background:#10b981;box-shadow:0 0 12px rgba(16,185,129,.8)}
    .track-account{color:var(--text-secondary);font-size:.88rem}
    .track-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.9rem}
    .track-card{background:rgba(255,255,255,.025);border:1px solid var(--border-color);border-radius:12px;padding:1rem;text-align:left}
    .track-card small{display:block;color:var(--text-secondary);margin-bottom:.3rem;font-size:.75rem}.track-card strong{font-size:1.15rem}.track-sub{display:block;color:var(--text-secondary);font-size:.72rem;margin-top:.25rem}
    .track-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}.track-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-chart{width:100%;height:220px;display:block}.track-chart-empty{height:180px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:.9rem}
    .track-table-wrap{overflow:auto}.track-table{width:100%;border-collapse:collapse;min-width:1050px;font-size:.8rem}.track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}.track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}.track-table th:last-child,.track-table td:last-child{font-weight:800}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}.track-method{color:var(--text-secondary);font-size:.78rem;line-height:1.55;text-align:left}.track-method strong{color:var(--text-primary)}
    .track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    .unified-live-panel .public-broadcast-shell,.unified-live-panel .live-mt5-shell{max-width:none;margin:0;width:100%}
    .unified-live-panel .public-broadcast-shell{border:1px solid rgba(16,185,129,.35);box-shadow:none}
    .unified-live-panel .live-mt5-shell{padding:1rem}
    #broadcast-slot[hidden],#telemetry-slot[hidden]{display:none!important}
    @media(max-width:600px){.track-card strong{font-size:1.02rem}.track-chart{height:180px}}
  `;
  document.head.appendChild(style);

  const fmtNumber = (value, digits = 2) => {
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits) : "—";
  };
  const fmtPercent = (value, digits = 2) => {
    const n = Number(value);
    return Number.isFinite(n) ? `${n.toFixed(digits)}%` : "—";
  };
  const fmtSignedPercent = (value, digits = 2) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`;
  };
  const fmtMoney = (value, currency = "USD") => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    try {
      return new Intl.NumberFormat(undefined,{style:"currency",currency:String(currency || "USD").toUpperCase(),minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
    } catch (_) {
      return `${String(currency || "USD").toUpperCase()} ${n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`;
    }
  };
  const fmtDate = (value) => {
    if (!value) return "—";
    const raw = String(value);
    const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw) ? `${raw}T00:00:00Z` : raw);
    return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  };
  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null ? "—" : String(value);
  }

  function buildUnifiedDisplay() {
    const broadcastShell = broadcastSection ? broadcastSection.querySelector(".public-broadcast-shell") : null;
    const liveShell = liveSection ? liveSection.querySelector(".live-mt5-shell") : null;

    performanceSection.innerHTML = `
      <div class="unified-live-title">
        <h2>LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1</h2>
        <p>One verified display combining the original live Bethel Terminal 1 broadcast, read-only MT5 telemetry and reconciled performance analytics for the same active master account.</p>
      </div>
      <div id="unified-live-panel" class="unified-live-panel">
        <div id="broadcast-slot" hidden></div>
        <div id="telemetry-slot" hidden></div>
        <div class="track-topbar">
          <span id="track-verification" class="track-verified"><span class="track-dot"></span> CHECKING RECORD</span>
          <span id="track-account" class="track-account">Active master · masked</span>
        </div>
        <div id="track-loading" class="track-loading">Loading verified performance…</div>
        <div id="track-content" hidden>
          <div class="track-grid">
            <div class="track-card"><small>Starting balance</small><strong id="track-starting-balance">—</strong><span class="track-sub">Same active-master starting capital used by Super Admin</span></div>
            <div class="track-card"><small>Current balance</small><strong id="track-current-balance">—</strong><span class="track-sub">Active-master balance</span></div>
            <div class="track-card"><small>Current equity</small><strong id="track-current-equity">—</strong><span class="track-sub">Live account equity</span></div>
            <div class="track-card"><small>Total return</small><strong id="track-total-return">—</strong><span class="track-sub">Active-master record</span></div>
            <div class="track-card"><small>Banked return</small><strong id="track-banked-return">—</strong><span class="track-sub">Closed-profit return basis</span></div>
            <div class="track-card"><small>Daily return</small><strong id="track-daily-return">—</strong><span class="track-sub">Super Admin Performance & Analytics</span></div>
            <div class="track-card"><small>Weekly return</small><strong id="track-weekly-return">—</strong><span class="track-sub">Super Admin Performance & Analytics</span></div>
            <div class="track-card"><small>Monthly return</small><strong id="track-monthly-return">—</strong><span class="track-sub">Super Admin Performance & Analytics</span></div>
            <div class="track-card"><small>History</small><strong id="track-history-days">—</strong><span class="track-sub" id="track-history-range">—</span></div>
            <div class="track-card"><small>Annualized return</small><strong id="track-annualized-return">—</strong><span class="track-sub">252 trading-day basis</span></div>
            <div class="track-card"><small>Maximum drawdown</small><strong id="track-max-dd">—</strong><span class="track-sub">Peak-to-valley</span></div>
            <div class="track-card"><small>Current drawdown</small><strong id="track-current-dd">—</strong><span class="track-sub">Latest high watermark</span></div>
            <div class="track-card"><small>Sharpe ratio</small><strong id="track-sharpe">—</strong><span class="track-sub">Risk-adjusted return</span></div>
            <div class="track-card"><small>Sortino ratio</small><strong id="track-sortino">—</strong><span class="track-sub">Downside-adjusted return</span></div>
            <div class="track-card"><small>Annualized volatility</small><strong id="track-volatility">—</strong><span class="track-sub">Daily return series</span></div>
            <div class="track-card"><small>Win rate</small><strong id="track-winrate">—</strong><span class="track-sub" id="track-trades">— trades</span></div>
            <div class="track-card"><small>Profit factor</small><strong id="track-profit-factor">—</strong><span class="track-sub">Gross profit / gross loss</span></div>
            <div class="track-card"><small>Performance grade</small><strong id="track-grade">—</strong><span class="track-sub" id="track-risk">Risk —</span></div>
            <div class="track-card"><small>All-time high return</small><strong id="track-ath">—</strong><span class="track-sub" id="track-ath-date">—</span></div>
          </div>
          <div class="track-panel"><h3>Balance & Equity History</h3><div id="track-chart-container" class="track-chart-empty">Loading history…</div></div>
          <div class="track-panel"><h3>Monthly & Yearly Returns</h3><div id="track-monthly" class="track-table-wrap"><span class="track-history-label">Awaiting reconciled monthly history…</span></div></div>
          <div class="track-panel track-method"><strong>Methodology & provenance</strong><br><span id="track-methodology">—</span><br><br>Read-only display. Account credentials, broker secrets, order tickets and execution controls are not published. Past performance does not guarantee future results.</div>
        </div>
      </div>`;

    const broadcastSlot = document.getElementById("broadcast-slot");
    const telemetrySlot = document.getElementById("telemetry-slot");
    if (broadcastShell && broadcastSlot) broadcastSlot.appendChild(broadcastShell);
    if (liveShell && telemetrySlot) telemetrySlot.appendChild(liveShell);

    if (broadcastSection && broadcastSection.isConnected) broadcastSection.remove();
    if (liveSection && liveSection.isConnected) liveSection.remove();
  }

  function renderChart(points) {
    const container = document.getElementById("track-chart-container");
    if (!container) return;
    const clean = (Array.isArray(points) ? points : []).filter(p => Number.isFinite(Number(p.equity)) && Number.isFinite(Number(p.balance)));
    if (clean.length < 2) {
      container.className = "track-chart-empty";
      container.textContent = clean.length === 1 ? "One verified history point is available; a chart requires at least two points." : "Verified balance/equity history is not yet available.";
      return;
    }
    const width = 1000, height = 220, pad = 16;
    const values = clean.flatMap(p => [Number(p.balance), Number(p.equity)]);
    let min = Math.min(...values), max = Math.max(...values);
    if (max === min) { max += 1; min -= 1; }
    const x = i => pad + (i * (width - pad * 2) / (clean.length - 1));
    const y = v => height - pad - ((v - min) * (height - pad * 2) / (max - min));
    const line = key => clean.map((p,i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(Number(p[key])).toFixed(1)}`).join(" ");
    container.className = "";
    container.innerHTML = `<svg class="track-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Balance and equity history"><path d="${line("balance")}" fill="none" stroke="#22d3ee" stroke-width="3" vector-effect="non-scaling-stroke"/><path d="${line("equity")}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><div class="track-history-label">Balance <span style="color:#22d3ee">●</span> &nbsp; Equity <span style="color:#10b981">●</span> · ${clean.length} sampled read-only points</div>`;
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
      container.innerHTML = '<span class="track-history-label">Reconciled monthly history is not available for the verified record window.</span>';
      return;
    }

    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const years = [...new Set(valid.map(r => String(r.period).slice(0,4)))].sort();
    const byMonth = new Map(valid.map(r => [String(r.period), Number(r.return_percent)]));
    const table = document.createElement("table");
    table.className = "track-table";
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    ["Year", ...months, "Year"].forEach(label => { const th=document.createElement("th"); th.textContent=label; hr.appendChild(th); });
    thead.appendChild(hr);
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
    note.textContent = `Calendar returns for the active master only · ${fmtDate(historyStart)} — ${fmtDate(historyEnd)}.`;
    container.appendChild(note);
  }

  async function fetchSummary() {
    const response = await fetch(`${API}/performance/public-summary?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}});
    if (!response.ok) throw new Error("summary unavailable");
    const data = await response.json();
    if (!data.available) throw new Error("track record unavailable");
    return data;
  }

  async function fetchHistory() {
    const response = await fetch(`${API}/performance/public-history?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}});
    if (!response.ok) return [];
    const data = await response.json();
    return data && Array.isArray(data.points) ? data.points : [];
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

  async function load() {
    if (loading) return;
    loading = true;
    try {
      const [data, history] = await Promise.all([fetchSummary(), fetchHistory()]);
      const summaryAgain = await fetchSummary();
      if (summaryAgain.account_number !== data.account_number) {
        throw new Error("active master changed during refresh");
      }

      setText("track-verification", `${String(data.verification_status || "VERIFIED").toUpperCase()} RECORD`);
      setText("track-account", `Active master · ${data.account_number || "masked"}`);
      setText("track-starting-balance", fmtMoney(data.starting_balance, data.currency));
      setText("track-current-balance", fmtMoney(data.current_balance, data.currency));
      setText("track-current-equity", fmtMoney(data.current_equity, data.currency));
      setText("track-total-return", fmtSignedPercent(data.total_return_percent));
      setText("track-banked-return", fmtSignedPercent(data.banked_return_percent));
      setText("track-daily-return", fmtSignedPercent(data.daily_return_percent));
      setText("track-weekly-return", fmtSignedPercent(data.weekly_return_percent));
      setText("track-monthly-return", fmtSignedPercent(data.monthly_return_percent));
      setText("track-history-days", Number.isFinite(Number(data.history_days)) ? `${Number(data.history_days).toFixed(2)} days` : "—");
      setText("track-history-range", data.history_start && data.history_end ? `${fmtDate(data.history_start)} — ${fmtDate(data.history_end)}` : "Active-master analytics history");
      setText("track-annualized-return", fmtSignedPercent(data.annualized_return_percent));
      setText("track-max-dd", fmtPercent(data.maximum_drawdown_percent));
      setText("track-current-dd", fmtPercent(data.current_drawdown_percent));
      setText("track-sharpe", fmtNumber(data.sharpe_ratio));
      setText("track-sortino", fmtNumber(data.sortino_ratio));
      setText("track-volatility", fmtPercent(data.annualized_volatility_percent));
      setText("track-winrate", fmtPercent(data.win_rate));
      setText("track-trades", `${Number(data.closed_deals ?? data.total_trades ?? 0)} closed trades`);
      setText("track-profit-factor", fmtNumber(data.profit_factor));
      setText("track-grade", data.performance_grade || "—");
      setText("track-risk", `Risk ${data.risk_level || "—"}`);
      setText("track-ath", fmtSignedPercent(data.all_time_high_return_percent));
      setText("track-ath-date", fmtDate(data.all_time_high_date));
      setText("track-methodology", data.methodology || "Read-only signed active-master snapshots and reconciled closed-trade history.");
      renderChart(history);
      renderMonthly(data.monthly_returns || [], data.history_start, data.history_end);
      const loadingEl = document.getElementById("track-loading");
      const contentEl = document.getElementById("track-content");
      if (loadingEl) loadingEl.hidden = true;
      if (contentEl) contentEl.hidden = false;
    } catch (_) {
      const loadingEl = document.getElementById("track-loading");
      if (loadingEl) { loadingEl.className="track-error"; loadingEl.hidden=false; loadingEl.textContent="Verified performance is temporarily unavailable or the active master is switching. No mixed-account record is displayed."; }
    } finally {
      loading = false;
    }
  }

  buildUnifiedDisplay();
  syncPublicVisibility();
  load();
  setInterval(syncPublicVisibility, 5000);
  setInterval(load, 15000);
})();
