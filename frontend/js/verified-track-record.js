(function () {
  "use strict";

  const API = "https://api.betheltradingtechnologies.com";
  const performance = document.getElementById("performance");
  if (!performance) return;

  const legacyBroadcast = document.getElementById("public-broadcast");
  const legacyTelemetry = document.getElementById("public-live-mt5");
  const broadcastShell = legacyBroadcast?.querySelector(".public-broadcast-shell") || null;
  const telemetryShell = legacyTelemetry?.querySelector(".live-mt5-shell") || null;

  const style = document.createElement("style");
  style.textContent = `
    #performance[hidden],#terminal1-video[hidden],#terminal1-telemetry[hidden]{display:none!important}
    #public-broadcast,#public-live-mt5{display:none!important}
    #performance{padding-top:4rem;padding-bottom:4rem}
    .terminal1-title{text-align:center;margin-bottom:1.5rem}
    .terminal1-title h2{font-size:clamp(1.65rem,3vw,2.25rem);margin-bottom:.55rem}
    .terminal1-title p{color:var(--text-secondary);max-width:760px;margin:0 auto}
    .terminal1-shell{background:var(--card-bg);border:1px solid rgba(16,185,129,.45);border-radius:18px;padding:1.25rem;display:grid;gap:1rem;box-shadow:0 0 28px rgba(16,185,129,.08)}
    .terminal1-shell .public-broadcast-shell,.terminal1-shell .live-mt5-shell{max-width:none;margin:0;width:100%}
    .terminal1-shell .public-broadcast-shell{border:1px solid rgba(16,185,129,.35);box-shadow:none}
    .terminal1-shell .live-mt5-shell{padding:1rem}
    .track-topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}
    .track-verified{display:inline-flex;align-items:center;gap:.5rem;border:1px solid rgba(16,185,129,.35);background:rgba(16,185,129,.08);color:#a7f3d0;border-radius:999px;padding:.5rem .8rem;font-weight:800;font-size:.78rem;letter-spacing:.05em}
    .track-dot{width:.55rem;height:.55rem;border-radius:50%;background:#10b981;box-shadow:0 0 12px rgba(16,185,129,.8)}
    .track-account{color:var(--text-secondary);font-size:.88rem}
    .track-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.9rem}
    .track-card{background:rgba(255,255,255,.025);border:1px solid var(--border-color);border-radius:12px;padding:1rem;text-align:left}
    .track-card small{display:block;color:var(--text-secondary);margin-bottom:.3rem;font-size:.75rem}
    .track-card strong{font-size:1.15rem}.track-sub{display:block;color:var(--text-secondary);font-size:.72rem;margin-top:.25rem}
    .track-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}
    .track-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-chart{width:100%;height:220px;display:block}.track-chart-empty{height:180px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:.9rem}
    .track-table-wrap{overflow:auto}.track-table{width:100%;border-collapse:collapse;min-width:720px;font-size:.8rem}
    .track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}
    .track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}
    .track-method{color:var(--text-secondary);font-size:.78rem;line-height:1.55;text-align:left}.track-method strong{color:var(--text-primary)}
    .track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    @media(max-width:600px){#performance{padding-top:3rem;padding-bottom:3rem}.track-card strong{font-size:1.02rem}.track-chart{height:180px}}
  `;
  document.head.appendChild(style);

  performance.hidden = true;
  performance.innerHTML = `
    <div class="terminal1-title">
      <h2>LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1</h2>
      <p>Live video, read-only MT5 telemetry and verified performance for one owner/master terminal.</p>
    </div>
    <div class="terminal1-shell">
      <div id="terminal1-video" hidden></div>
      <div id="terminal1-telemetry" hidden></div>
      <div class="track-topbar">
        <span id="track-verification" class="track-verified"><span class="track-dot"></span> CHECKING RECORD</span>
        <span id="track-account" class="track-account">Bethel Terminal 1 · masked</span>
      </div>
      <div id="track-loading" class="track-loading">Loading verified performance…</div>
      <div id="track-content" hidden>
        <div class="track-grid">
          <div class="track-card"><small>Total return</small><strong id="track-total-return">—</strong><span class="track-sub">Active-master record</span></div>
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
          <div class="track-card"><small>History</small><strong id="track-history-days">—</strong><span class="track-sub" id="track-history-range">—</span></div>
        </div>
        <div class="track-panel"><h3>Balance & Equity History</h3><div id="track-chart-container" class="track-chart-empty">Loading history…</div></div>
        <div class="track-panel"><h3>Monthly Returns</h3><div id="track-monthly" class="track-table-wrap"><span class="track-history-label">Awaiting reconciled monthly history…</span></div></div>
        <div class="track-panel track-method"><strong>Methodology & provenance</strong><br><span id="track-methodology">—</span><br><br>Read-only display. Account credentials, broker secrets, order tickets and execution controls are not published. Past performance does not guarantee future results.</div>
      </div>
    </div>`;

  const videoSlot = document.getElementById("terminal1-video");
  const telemetrySlot = document.getElementById("terminal1-telemetry");
  if (broadcastShell) videoSlot.appendChild(broadcastShell);
  if (telemetryShell) telemetrySlot.appendChild(telemetryShell);

  // Remove only the legacy wrappers. Existing inline workers retain references to
  // the moved video/telemetry elements, so live updating continues without duplicate DOM.
  legacyBroadcast?.remove();
  legacyTelemetry?.remove();

  // Canonical public order: Hero -> Terminal 1 -> About -> Services -> ...
  const hero = document.querySelector("section.hero");
  if (hero) hero.insertAdjacentElement("afterend", performance);

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null ? "—" : String(value);
  };
  const number = (v,d=2) => Number.isFinite(Number(v)) ? Number(v).toFixed(d) : "—";
  const percent = (v,d=2) => Number.isFinite(Number(v)) ? `${Number(v).toFixed(d)}%` : "—";
  const signedPercent = (v,d=2) => Number.isFinite(Number(v)) ? `${Number(v)>0?"+":""}${Number(v).toFixed(d)}%` : "—";
  const date = v => {
    if (!v) return "—";
    const d = new Date(`${v}T00:00:00Z`);
    return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  };

  function renderChart(points) {
    const container = document.getElementById("track-chart-container");
    const clean = (Array.isArray(points)?points:[]).filter(p=>Number.isFinite(Number(p.balance))&&Number.isFinite(Number(p.equity)));
    if (!container || clean.length < 2) {
      if (container) container.textContent = "Not enough history to draw the chart yet.";
      return;
    }
    const width=1000,height=220,pad=16,values=clean.flatMap(p=>[Number(p.balance),Number(p.equity)]);
    let min=Math.min(...values),max=Math.max(...values); if(max===min){max+=1;min-=1;}
    const x=i=>pad+i*(width-pad*2)/(clean.length-1), y=v=>height-pad-(v-min)*(height-pad*2)/(max-min);
    const line=key=>clean.map((p,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(Number(p[key])).toFixed(1)}`).join(" ");
    container.className="";
    container.innerHTML=`<svg class="track-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Balance and equity history"><path d="${line("balance")}" fill="none" stroke="#22d3ee" stroke-width="3" vector-effect="non-scaling-stroke"/><path d="${line("equity")}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><div class="track-history-label">Balance <span style="color:#22d3ee">●</span> &nbsp; Equity <span style="color:#10b981">●</span> · ${clean.length} sampled read-only points</div>`;
  }

  function renderMonthly(rows) {
    const container=document.getElementById("track-monthly");
    if(!container)return;
    const valid=(Array.isArray(rows)?rows:[]).filter(r=>/^\d{4}-\d{2}$/.test(String(r.period||""))&&Number.isFinite(Number(r.return_percent)));
    if(!valid.length){container.innerHTML='<span class="track-history-label">Reconciled monthly history is not available yet.</span>';return;}
    const years=[...new Set(valid.map(r=>r.period.slice(0,4)))].sort(),map=new Map(valid.map(r=>[r.period,Number(r.return_percent)])),months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    let html='<table class="track-table"><thead><tr><th>Year</th>'+months.map(m=>`<th>${m}</th>`).join("")+'<th>Year</th></tr></thead><tbody>';
    years.forEach(year=>{
      let vals=[]; html+=`<tr><td>${year}</td>`;
      for(let m=1;m<=12;m++){const v=map.get(`${year}-${String(m).padStart(2,"0")}`);if(Number.isFinite(v)){vals.push(v/100);html+=`<td class="${v>0?"track-positive":v<0?"track-negative":"track-neutral"}">${signedPercent(v)}</td>`;}else html+='<td>—</td>';}
      const annual=vals.length?(vals.reduce((f,r)=>f*(1+r),1)-1)*100:NaN; html+=`<td class="${annual>0?"track-positive":annual<0?"track-negative":"track-neutral"}">${Number.isFinite(annual)?signedPercent(annual):"—"}</td></tr>`;
    });
    container.innerHTML=html+'</tbody></table>';
  }

  async function refreshVisibility() {
    videoSlot.hidden = true;
    telemetrySlot.hidden = true;
    performance.hidden = true;
    try {
      const [b,t] = await Promise.all([
        fetch(`${API}/broadcast/v1/public/status?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}}).then(r=>r.ok?r.json():null),
        fetch(`${API}/connector/v1/public/live?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}}).then(r=>r.ok?r.json():null)
      ]);
      const videoOn = b?.enabled === true;
      const telemetryOn = t?.enabled === true;
      videoSlot.hidden = !videoOn;
      telemetrySlot.hidden = !telemetryOn;
      performance.hidden = !(videoOn || telemetryOn);
    } catch (_) {
      videoSlot.hidden = true;
      telemetrySlot.hidden = true;
      performance.hidden = true;
    }
  }

  let loading=false;
  async function loadPerformance() {
    if(loading)return; loading=true;
    try {
      const r=await fetch(`${API}/performance/public-summary?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}});
      if(!r.ok)throw new Error();
      const d=await r.json(); if(!d.available)throw new Error();
      setText("track-verification",`${String(d.verification_status||"VERIFIED").toUpperCase()} RECORD`);
      setText("track-account",`Bethel Terminal 1 · ${d.account_mask||"masked"}`);
      setText("track-total-return",signedPercent(d.total_return_percent));
      setText("track-annualized-return",signedPercent(d.annualized_return_percent));
      setText("track-max-dd",percent(d.maximum_drawdown_percent));
      setText("track-current-dd",percent(d.current_drawdown_percent));
      setText("track-sharpe",number(d.sharpe_ratio)); setText("track-sortino",number(d.sortino_ratio));
      setText("track-volatility",percent(d.annualized_volatility_percent)); setText("track-winrate",percent(d.win_rate_percent));
      setText("track-trades",`${Number(d.closed_trades||0)} closed trades`); setText("track-profit-factor",number(d.profit_factor));
      setText("track-grade",d.performance_grade||"—"); setText("track-risk",`Risk ${d.risk_level||"—"}`);
      setText("track-ath",signedPercent(d.all_time_high_return_percent)); setText("track-ath-date",date(d.all_time_high_date));
      setText("track-history-days",`${Number(d.history_days||0)} days`); setText("track-history-range",`${date(d.history_start)} — ${date(d.history_end)}`);
      setText("track-methodology",d.methodology||"Read-only signed active-master snapshots and reconciled closed-trade history.");
      renderChart(d.history||[]); renderMonthly(d.monthly_returns||[]);
      document.getElementById("track-loading").hidden=true; document.getElementById("track-content").hidden=false;
    } catch (_) {
      const el=document.getElementById("track-loading"); if(el){el.className="track-error";el.textContent="Verified performance is temporarily unavailable.";}
    } finally { loading=false; }
  }

  refreshVisibility();
  loadPerformance();
  setInterval(refreshVisibility,3000);
  setInterval(loadPerformance,60000);
})();