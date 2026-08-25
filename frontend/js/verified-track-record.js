(function () {
  "use strict";

  const API = "https://api.betheltradingtechnologies.com";
  const performanceSection = document.getElementById("performance");
  const broadcastSection = document.getElementById("public-broadcast");
  const liveSection = document.getElementById("public-live-mt5");
  if (!performanceSection) return;

  let loading = false;
  let visibilityLoading = false;

  const style = document.createElement("style");
  style.textContent = `
    #performance[hidden]{display:none!important}
    #broadcast-slot[hidden],#telemetry-slot[hidden]{display:none!important}
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
    .track-card small{display:block;color:var(--text-secondary);margin-bottom:.3rem;font-size:.75rem}
    .track-card strong{font-size:1.15rem}
    .track-sub{display:block;color:var(--text-secondary);font-size:.72rem;margin-top:.25rem}
    .track-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}
    .track-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-chart{width:100%;height:220px;display:block}
    .track-chart-empty{height:180px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:.9rem}
    .track-table-wrap{overflow:auto}
    .track-table{width:100%;border-collapse:collapse;min-width:720px;font-size:.8rem}
    .track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}
    .track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}
    .track-method{color:var(--text-secondary);font-size:.78rem;line-height:1.55;text-align:left}.track-method strong{color:var(--text-primary)}
    .track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    .unified-live-panel .public-broadcast-shell,.unified-live-panel .live-mt5-shell{max-width:none;margin:0;width:100%}
    .unified-live-panel .public-broadcast-shell{border:1px solid rgba(16,185,129,.35);box-shadow:none}
    .unified-live-panel .live-mt5-shell{padding:1rem}
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
  const fmtDate = value => {
    if (!value) return "—";
    const d = new Date(`${value}T00:00:00Z`);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"});
  };
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null ? "—" : String(value);
  };

  function buildUnifiedDisplay() {
    const broadcastShell = broadcastSection ? broadcastSection.querySelector(".public-broadcast-shell") : null;
    const liveShell = liveSection ? liveSection.querySelector(".live-mt5-shell") : null;

    performanceSection.hidden = true;
    performanceSection.innerHTML = `
      <div class="unified-live-title">
        <h2>LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1</h2>
        <p>Live video, read-only MT5 telemetry and verified performance for the same owner/master terminal.</p>
      </div>
      <div id="unified-live-panel" class="unified-live-panel">
        <div id="broadcast-slot" hidden></div>
        <div id="telemetry-slot" hidden></div>
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

    const broadcastSlot = document.getElementById("broadcast-slot");
    const telemetrySlot = document.getElementById("telemetry-slot");
    if (broadcastShell && broadcastSlot) broadcastSlot.appendChild(broadcastShell);
    if (liveShell && telemetrySlot) telemetrySlot.appendChild(liveShell);

    // Permanently remove the legacy public section wrappers. Their inline timers may
    // retain references, but detached wrappers can no longer create duplicate headings
    // or reserve vertical space. The actual video/telemetry shells remain live above.
    if (broadcastSection) broadcastSection.remove();
    if (liveSection) liveSection.remove();

    // Keep one canonical location: immediately below the hero and before About Us.
    const hero = document.querySelector("section.hero");
    if (hero && hero.nextElementSibling !== performanceSection) {
      hero.insertAdjacentElement("afterend", performanceSection);
    }
  }

  async function refreshSuperAdminVisibility() {
    if (visibilityLoading) return;
    visibilityLoading = true;
    const broadcastSlot = document.getElementById("broadcast-slot");
    const telemetrySlot = document.getElementById("telemetry-slot");
    if (!broadcastSlot || !telemetrySlot) { visibilityLoading = false; return; }

    // Fail closed on every refresh. Nothing is shown unless the authoritative
    // public endpoints explicitly confirm Super Admin publication is enabled.
    broadcastSlot.hidden = true;
    telemetrySlot.hidden = true;
    performanceSection.hidden = true;

    let videoEnabled = false;
    let telemetryEnabled = false;
    try {
      const [broadcastResult, telemetryResult] = await Promise.allSettled([
        fetch(`${API}/broadcast/v1/public/status?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}}),
        fetch(`${API}/connector/v1/public/live?ts=${Date.now()}`, {cache:"no-store",headers:{Accept:"application/json"}})
      ]);

      if (broadcastResult.status === "fulfilled" && broadcastResult.value.ok) {
        const config = await broadcastResult.value.json();
        videoEnabled = config.enabled === true;
      }
      if (telemetryResult.status === "fulfilled" && telemetryResult.value.ok) {
        const config = await telemetryResult.value.json();
        telemetryEnabled = config.enabled === true;
      }
    } catch (_) {
      videoEnabled = false;
      telemetryEnabled = false;
    }

    broadcastSlot.hidden = !videoEnabled;
    telemetrySlot.hidden = !telemetryEnabled;
    performanceSection.hidden = !(videoEnabled || telemetryEnabled);
    visibilityLoading = false;
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
    const width=1000,height=220,pad=16;
    const values=clean.flatMap(p=>[Number(p.balance),Number(p.equity)]);
    let min=Math.min(...values),max=Math.max(...values);
    if(max===min){max+=1;min-=1;}
    const x=i=>pad+(i*(width-pad*2)/(clean.length-1));
    const y=v=>height-pad-((v-min)*(height-pad*2)/(max-min));
    const line=key=>clean.map((p,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(Number(p[key])).toFixed(1)}`).join(" ");
    container.className="";
    container.innerHTML=`<svg class="track-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Balance and equity history"><path d="${line("balance")}" fill="none" stroke="#22d3ee" stroke-width="3" vector-effect="non-scaling-stroke"/><path d="${line("equity")}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><div class="track-history-label">Balance <span style="color:#22d3ee">●</span> &nbsp; Equity <span style="color:#10b981">●</span> · ${clean.length} sampled read-only points</div>`;
  }

  function renderMonthly(rows) {
    const container=document.getElementById("track-monthly");
    if(!container)return;
    const valid=(Array.isArray(rows)?rows:[]).filter(r=>/^\d{4}-\d{2}$/.test(String(r.period||""))&&Number.isFinite(Number(r.return_percent)));
    if(!valid.length){container.innerHTML='<span class="track-history-label">Reconciled monthly history is not available yet.</span>';return;}
    const years=[...new Set(valid.map(r=>r.period.slice(0,4)))].sort();
    const byMonth=new Map(valid.map(r=>[r.period,Number(r.return_percent)]));
    const months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const table=document.createElement("table");table.className="track-table";
    const thead=document.createElement("thead"),hr=document.createElement("tr");
    ["Year",...months,"Year"].forEach(label=>{const th=document.createElement("th");th.textContent=label;hr.appendChild(th);});
    thead.appendChild(hr);table.appendChild(thead);
    const tbody=document.createElement("tbody");
    years.forEach(year=>{
      const tr=document.createElement("tr"),yc=document.createElement("td");yc.textContent=year;tr.appendChild(yc);const vals=[];
      for(let m=1;m<=12;m++){
        const key=`${year}-${String(m).padStart(2,"0")}`,value=byMonth.get(key),td=document.createElement("td");
        if(Number.isFinite(value)){td.textContent=fmtSignedPercent(value);td.className=value>0?"track-positive":value<0?"track-negative":"track-neutral";vals.push(value/100);}else td.textContent="—";
        tr.appendChild(td);
      }
      const annual=vals.length?(vals.reduce((f,r)=>f*(1+r),1)-1)*100:NaN,total=document.createElement("td");
      total.textContent=Number.isFinite(annual)?fmtSignedPercent(annual):"—";total.className=annual>0?"track-positive":annual<0?"track-negative":"track-neutral";tr.appendChild(total);tbody.appendChild(tr);
    });
    table.appendChild(tbody);container.innerHTML="";container.appendChild(table);
  }

  async function fetchSummary() {
    const response=await fetch(`${API}/performance/public-summary?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}});
    if(!response.ok)throw new Error("summary unavailable");
    const data=await response.json();
    if(!data.available)throw new Error("track record unavailable");
    return data;
  }

  async function load() {
    if(loading)return;
    loading=true;
    try{
      const data=await fetchSummary();
      setText("track-verification",`${String(data.verification_status||"VERIFIED").toUpperCase()} RECORD`);
      setText("track-account",`Bethel Terminal 1 · ${data.account_mask||"masked"}`);
      setText("track-total-return",fmtSignedPercent(data.total_return_percent));
      setText("track-annualized-return",fmtSignedPercent(data.annualized_return_percent));
      setText("track-max-dd",fmtPercent(data.maximum_drawdown_percent));
      setText("track-current-dd",fmtPercent(data.current_drawdown_percent));
      setText("track-sharpe",fmtNumber(data.sharpe_ratio));
      setText("track-sortino",fmtNumber(data.sortino_ratio));
      setText("track-volatility",fmtPercent(data.annualized_volatility_percent));
      setText("track-winrate",fmtPercent(data.win_rate_percent));
      setText("track-trades",`${Number(data.closed_trades||0)} closed trades`);
      setText("track-profit-factor",fmtNumber(data.profit_factor));
      setText("track-grade",data.performance_grade||"—");
      setText("track-risk",`Risk ${data.risk_level||"—"}`);
      setText("track-ath",fmtSignedPercent(data.all_time_high_return_percent));
      setText("track-ath-date",fmtDate(data.all_time_high_date));
      setText("track-history-days",`${Number(data.history_days||0)} days`);
      setText("track-history-range",`${fmtDate(data.history_start)} — ${fmtDate(data.history_end)}`);
      setText("track-methodology",data.methodology||"Read-only signed active-master snapshots and reconciled closed-trade history.");
      renderChart(data.history||[]);renderMonthly(data.monthly_returns||[]);
      const loadingEl=document.getElementById("track-loading"),contentEl=document.getElementById("track-content");
      if(loadingEl)loadingEl.hidden=true;if(contentEl)contentEl.hidden=false;
    }catch(_){
      const loadingEl=document.getElementById("track-loading");
      if(loadingEl){loadingEl.className="track-error";loadingEl.textContent="Verified performance is temporarily unavailable.";}
    }finally{loading=false;}
  }

  buildUnifiedDisplay();
  refreshSuperAdminVisibility();
  load();
  setInterval(refreshSuperAdminVisibility,3000);
  setInterval(load,60000);
})();