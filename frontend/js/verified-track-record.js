(function () {
  "use strict";

  const API = "https://api.betheltradingtechnologies.com";
  const performanceSection = document.getElementById("performance");
  const liveSection = document.getElementById("public-live-mt5");
  if (!performanceSection) return;

  const style = document.createElement("style");
  style.textContent = `
    .track-shell{display:grid;gap:1.25rem}.track-topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}.track-verified{display:inline-flex;align-items:center;gap:.5rem;border:1px solid rgba(16,185,129,.35);background:rgba(16,185,129,.08);color:#a7f3d0;border-radius:999px;padding:.5rem .8rem;font-weight:800;font-size:.78rem;letter-spacing:.05em}.track-dot{width:.55rem;height:.55rem;border-radius:50%;background:#10b981;box-shadow:0 0 12px rgba(16,185,129,.8)}.track-account{color:var(--text-secondary);font-size:.88rem}.track-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.9rem}.track-card{background:rgba(255,255,255,.025);border:1px solid var(--border-color);border-radius:12px;padding:1rem;text-align:left}.track-card small{display:block;color:var(--text-secondary);margin-bottom:.3rem;font-size:.75rem}.track-card strong{font-size:1.15rem}.track-sub{display:block;color:var(--text-secondary);font-size:.72rem;margin-top:.25rem}.track-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}.track-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}.track-chart{width:100%;height:220px;display:block}.track-chart-empty{height:180px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:.9rem}.track-table-wrap{overflow:auto}.track-table{width:100%;border-collapse:collapse;min-width:720px;font-size:.8rem}.track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}.track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}.track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}.track-method{color:var(--text-secondary);font-size:.78rem;line-height:1.55;text-align:left}.track-method strong{color:var(--text-primary)}.track-live-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:.75rem;margin-top:1rem}.track-live-item{background:rgba(16,185,129,.04);border:1px solid rgba(16,185,129,.18);border-radius:10px;padding:.75rem}.track-live-item small{display:block;color:var(--text-secondary);font-size:.7rem}.track-live-item strong{font-size:.95rem}.track-loading{color:var(--text-secondary);padding:1.5rem 0}.track-error{color:#fca5a5;padding:1.5rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}.track-heading-copy{color:var(--text-secondary);max-width:720px;margin:.4rem auto 0}@media(max-width:600px){.track-card strong{font-size:1.02rem}.track-chart{height:180px}}
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
  const fmtDate = (value) => {
    if (!value) return "—";
    const d = new Date(`${value}T00:00:00Z`);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  };

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null ? "—" : String(value);
  }

  function buildSkeleton() {
    performanceSection.innerHTML = `
      <div class="section-header">
        <h2>Verified Track Record</h2>
        <p class="track-heading-copy">Read-only performance from Bethel's active-master records, with cash-flow-neutral risk analytics derived from signed deals and cash flows.</p>
      </div>
      <div class="performance-box track-shell">
        <div class="track-topbar">
          <span id="track-verification" class="track-verified"><span class="track-dot"></span> CHECKING RECORD</span>
          <span id="track-account" class="track-account">Active master · masked</span>
        </div>
        <div id="track-loading" class="track-loading">Loading verified performance…</div>
        <div id="track-content" hidden>
          <div class="track-grid">
            <div class="track-card"><small>Total return</small><strong id="track-total-return">—</strong><span class="track-sub">Published track record</span></div>
            <div class="track-card"><small>Annualized return</small><strong id="track-annualized-return">—</strong><span class="track-sub">252 trading-day basis</span></div>
            <div class="track-card"><small>Maximum drawdown</small><strong id="track-max-dd">—</strong><span class="track-sub">Peak-to-valley</span></div>
            <div class="track-card"><small>Current drawdown</small><strong id="track-current-dd">—</strong><span class="track-sub">From latest high watermark</span></div>
            <div class="track-card"><small>Sharpe ratio</small><strong id="track-sharpe">—</strong><span class="track-sub">Risk-adjusted return</span></div>
            <div class="track-card"><small>Sortino ratio</small><strong id="track-sortino">—</strong><span class="track-sub">Downside-adjusted return</span></div>
            <div class="track-card"><small>Annualized volatility</small><strong id="track-volatility">—</strong><span class="track-sub">Daily return series</span></div>
            <div class="track-card"><small>Win rate</small><strong id="track-winrate">—</strong><span class="track-sub" id="track-trades">— trades</span></div>
            <div class="track-card"><small>Profit factor</small><strong id="track-profit-factor">—</strong><span class="track-sub">Gross profit / gross loss</span></div>
            <div class="track-card"><small>Performance grade</small><strong id="track-grade">—</strong><span class="track-sub" id="track-risk">Risk —</span></div>
            <div class="track-card"><small>All-time high return</small><strong id="track-ath">—</strong><span class="track-sub" id="track-ath-date">—</span></div>
            <div class="track-card"><small>History</small><strong id="track-history-days">—</strong><span class="track-sub" id="track-history-range">—</span></div>
          </div>
          <div class="track-panel"><h3>Balance & Equity History</h3><div id="track-chart-container" class="track-chart-empty">Loading history…</div></div>
          <div class="track-panel"><h3>Monthly Returns</h3><div id="track-monthly" class="track-table-wrap"><span class="track-history-label">Awaiting reconciled monthly history…</span></div></div>
          <div class="track-panel track-method"><strong>Methodology & provenance</strong><br><span id="track-methodology">—</span><br><br>Account credentials, broker secrets, order tickets and execution controls are never published. Past performance does not guarantee future results.</div>
        </div>
      </div>`;
  }

  function renderChart(points) {
    const container = document.getElementById("track-chart-container");
    if (!container) return;
    const clean = (Array.isArray(points) ? points : []).filter(p => Number.isFinite(Number(p.equity)) && Number.isFinite(Number(p.balance)));
    if (clean.length < 2) {
      container.className = "track-chart-empty";
      container.textContent = "Not enough history to draw the chart yet.";
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

  function renderMonthly(rows) {
    const container = document.getElementById("track-monthly");
    if (!container) return;
    const valid = (Array.isArray(rows) ? rows : []).filter(r => /^\d{4}-\d{2}$/.test(String(r.period || "")) && Number.isFinite(Number(r.return_percent)));
    if (!valid.length) {
      container.innerHTML = '<span class="track-history-label">Reconciled monthly history is not available yet.</span>';
      return;
    }
    const years = [...new Set(valid.map(r => r.period.slice(0,4)))].sort();
    const byMonth = new Map(valid.map(r => [r.period, Number(r.return_percent)]));
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const table = document.createElement("table");
    table.className = "track-table";
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    ["Year", ...months, "Year"].forEach(label => { const th=document.createElement("th"); th.textContent=label; hr.appendChild(th); });
    thead.appendChild(hr); table.appendChild(thead);
    const tbody = document.createElement("tbody");
    years.forEach(year => {
      const tr = document.createElement("tr");
      const yearCell = document.createElement("td"); yearCell.textContent=year; tr.appendChild(yearCell);
      const yearValues = [];
      for (let m=1;m<=12;m++) {
        const key = `${year}-${String(m).padStart(2,"0")}`;
        const value = byMonth.get(key);
        const td = document.createElement("td");
        if (Number.isFinite(value)) {
          td.textContent = fmtSignedPercent(value);
          td.className = value > 0 ? "track-positive" : value < 0 ? "track-negative" : "track-neutral";
          yearValues.push(value / 100);
        } else td.textContent = "—";
        tr.appendChild(td);
      }
      const annual = yearValues.length ? (yearValues.reduce((factor,r)=>factor*(1+r),1)-1)*100 : NaN;
      const total = document.createElement("td");
      total.textContent = Number.isFinite(annual) ? fmtSignedPercent(annual) : "—";
      total.className = annual > 0 ? "track-positive" : annual < 0 ? "track-negative" : "track-neutral";
      tr.appendChild(total); tbody.appendChild(tr);
    });
    table.appendChild(tbody); container.innerHTML=""; container.appendChild(table);
  }

  function attachLiveStrip(data) {
    if (!liveSection || !data || !data.available) return;
    const legacyShowcase = document.getElementById("bethel-performance-showcase");
    if (legacyShowcase) legacyShowcase.remove();
    let strip = document.getElementById("public-track-live-strip");
    if (!strip) {
      strip = document.createElement("div");
      strip.id = "public-track-live-strip";
      strip.className = "track-live-strip";
      const shell = liveSection.querySelector(".live-mt5-shell");
      if (shell) shell.appendChild(strip);
    }
    if (!strip) return;
    strip.innerHTML = `<div class="track-live-item"><small>Track Return</small><strong>${fmtSignedPercent(data.total_return_percent)}</strong></div><div class="track-live-item"><small>Max Drawdown</small><strong>${fmtPercent(data.maximum_drawdown_percent)}</strong></div><div class="track-live-item"><small>Sharpe</small><strong>${fmtNumber(data.sharpe_ratio)}</strong></div><div class="track-live-item"><small>Sortino</small><strong>${fmtNumber(data.sortino_ratio)}</strong></div><div class="track-live-item"><small>Ledger Status</small><strong>${String(data.verification_status || "READ ONLY")}</strong></div>`;
  }

  async function load() {
    buildSkeleton();
    try {
      const [summaryResponse, historyResponse] = await Promise.all([
        fetch(`${API}/performance/public-summary?ts=${Date.now()}`, {cache:"no-store", headers:{Accept:"application/json"}}),
        fetch(`${API}/performance/public-history?ts=${Date.now()}`, {cache:"no-store", headers:{Accept:"application/json"}})
      ]);
      if (!summaryResponse.ok) throw new Error("summary unavailable");
      const data = await summaryResponse.json();
      const history = historyResponse.ok ? await historyResponse.json() : {points:[]};
      if (!data.available) throw new Error("track record unavailable");

      setText("track-verification", `${data.verification_status || "READ ONLY"} · ${data.verification_scope || "ACTIVE MASTER"}`);
      const badge = document.getElementById("track-verification");
      if (badge && !badge.querySelector(".track-dot")) badge.insertAdjacentHTML("afterbegin",'<span class="track-dot"></span>');
      setText("track-account", `Active master ${data.account_number || "masked"} · ${data.currency || "USD"}`);
      setText("track-total-return", fmtSignedPercent(data.total_return_percent));
      setText("track-annualized-return", fmtSignedPercent(data.annualized_return_percent));
      setText("track-max-dd", fmtPercent(data.maximum_drawdown_percent));
      setText("track-current-dd", fmtSignedPercent(data.current_drawdown_percent));
      setText("track-sharpe", fmtNumber(data.sharpe_ratio));
      setText("track-sortino", fmtNumber(data.sortino_ratio));
      setText("track-volatility", fmtPercent(data.annualized_volatility_percent));
      setText("track-winrate", fmtPercent(data.win_rate));
      setText("track-trades", `${Number(data.total_trades || 0).toLocaleString()} trades`);
      setText("track-profit-factor", fmtNumber(data.profit_factor));
      setText("track-grade", data.performance_grade || "—");
      setText("track-risk", `Risk ${data.risk_level || "—"}`);
      setText("track-ath", fmtSignedPercent(data.all_time_high_return_percent));
      setText("track-ath-date", data.all_time_high_date ? `${fmtDate(data.all_time_high_date)} · ${Number(data.days_since_all_time_high || 0)} days since` : "—");
      setText("track-history-days", `${Number(data.trading_days || 0).toLocaleString()} trading days`);
      setText("track-history-range", data.history_start && data.history_end ? `${fmtDate(data.history_start)} → ${fmtDate(data.history_end)}` : "—");
      setText("track-methodology", data.methodology || "Read-only performance derived from recorded active-master history.");
      renderChart(history.points || []);
      renderMonthly(data.monthly_returns || []);
      attachLiveStrip(data);
      document.getElementById("track-loading").hidden = true;
      document.getElementById("track-content").hidden = false;
    } catch (error) {
      const loading = document.getElementById("track-loading");
      if (loading) { loading.className = "track-error"; loading.textContent = "Verified track record is temporarily unavailable. No fallback or demo figures are displayed."; }
    }
  }

  window.addEventListener("load", function () {
    load();
    window.setInterval(load, 60000);
  }, {once:true});
})();
