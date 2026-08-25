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
    .track-history-heading{margin-top:.25rem;padding-top:.25rem}
    .track-history-heading h3{font-size:1.15rem;margin-bottom:.25rem}
    .track-history-heading p{color:var(--text-secondary);font-size:.82rem}
    .track-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}
    .track-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-chart{width:100%;height:240px;display:block}
    .track-chart-empty{height:190px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:.9rem;text-align:center;padding:1rem}
    .track-chart-legend{display:flex;gap:1rem;flex-wrap:wrap;color:var(--text-secondary);font-size:.78rem;margin-top:.5rem}
    .track-table-wrap{overflow:auto}.track-table{width:100%;border-collapse:collapse;min-width:760px;font-size:.8rem}
    .track-table th,.track-table td{padding:.58rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}
    .track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}
    .track-method{color:var(--text-secondary);font-size:.78rem;line-height:1.55;text-align:left}.track-method strong{color:var(--text-primary)}
    .track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    @media(max-width:600px){#performance{padding-top:3rem;padding-bottom:3rem}.track-card strong{font-size:1.02rem}.track-chart{height:190px}}
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
          <div class="track-card"><small>Total return</small><strong id="track-total-return">—</strong><span class="track-sub">Verified record</span></div>
          <div class="track-card"><small>Annualized return</small><strong id="track-annualized-return">—</strong><span class="track-sub">252 trading-day basis</span></div>
          <div class="track-card"><small>Maximum drawdown</small><strong id="track-max-dd">—</strong><span class="track-sub">Peak-to-valley</span></div>
          <div class="track-card"><small>Current drawdown</small><strong id="track-current-dd">—</strong><span class="track-sub">Latest high watermark</span></div>
          <div class="track-card"><small>Sharpe ratio</small><strong id="track-sharpe">—</strong><span class="track-sub">Risk-adjusted return</span></div>
          <div class="track-card"><small>Sortino ratio</small><strong id="track-sortino">—</strong><span class="track-sub">Downside-adjusted return</span></div>
          <div class="track-card"><small>Annualized volatility</small><strong id="track-volatility">—</strong><span class="track-sub">Return variability</span></div>
          <div class="track-card"><small>Win rate</small><strong id="track-winrate">—</strong><span class="track-sub" id="track-trades">— trades</span></div>
          <div class="track-card"><small>Profit factor</small><strong id="track-profit-factor">—</strong><span class="track-sub">Gross profit / gross loss</span></div>
          <div class="track-card"><small>Performance grade</small><strong id="track-grade">—</strong><span class="track-sub" id="track-risk">Risk —</span></div>
          <div class="track-card"><small>All-time high return</small><strong id="track-ath">—</strong><span class="track-sub" id="track-ath-date">—</span></div>
          <div class="track-card"><small>Record history</small><strong id="track-history-days">—</strong><span class="track-sub" id="track-history-range">—</span></div>
        </div>

        <div class="track-history-heading">
          <h3>Verified Performance History</h3>
          <p>Historical balance, equity, growth and monthly returns derived from the same read-only Terminal 1 record.</p>
        </div>
        <div class="track-panel"><h3>Balance & Equity History</h3><div id="track-chart-container" class="track-chart-empty">Loading historical balance and equity…</div></div>
        <div class="track-panel"><h3>Cumulative Growth History</h3><div id="track-growth-container" class="track-chart-empty">Loading cumulative growth…</div></div>
        <div class="track-panel"><h3>Monthly Returns Record</h3><div id="track-monthly" class="track-table-wrap"><span class="track-history-label">Loading reconciled monthly history…</span></div></div>
        <div class="track-panel track-method"><strong>Methodology & provenance</strong><br><span id="track-methodology">—</span><br><br>Read-only display. Account credentials, broker secrets, order tickets and execution controls are not published. Past performance does not guarantee future results.</div>
      </div>
    </div>`;

  const videoSlot = document.getElementById("terminal1-video");
  const telemetrySlot = document.getElementById("terminal1-telemetry");
  if (broadcastShell) videoSlot.appendChild(broadcastShell);
  if (telemetryShell) telemetrySlot.appendChild(telemetryShell);
  legacyBroadcast?.remove();
  legacyTelemetry?.remove();

  const hero = document.querySelector("section.hero");
  if (hero) hero.insertAdjacentElement("afterend", performance);

  const setText=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value==null?"—":String(value)};
  const finite=v=>Number.isFinite(Number(v));
  const number=(v,d=2)=>finite(v)?Number(v).toFixed(d):"—";
  const percent=(v,d=2)=>finite(v)?`${Number(v).toFixed(d)}%`:"—";
  const signedPercent=(v,d=2)=>finite(v)?`${Number(v)>0?"+":""}${Number(v).toFixed(d)}%`:"—";
  const date=v=>{if(!v)return"—";const raw=String(v);const d=new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw)?`${raw}T00:00:00Z`:raw);return Number.isNaN(d.getTime())?raw:d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"})};

  function normalizeHistory(data){
    const sources=[data.history,data.equity_history,data.balance_history,data.performance_history,data.snapshots,data.timeseries,data.time_series,data.curve];
    const rows=sources.find(Array.isArray)||[];
    return rows.map((p,i)=>{
      if(Array.isArray(p)) return {date:p[0]??i,balance:Number(p[1]),equity:Number(p[2]??p[1])};
      const balance=p?.balance??p?.account_balance??p?.bal??p?.value;
      const equity=p?.equity??p?.account_equity??p?.eq??balance;
      const when=p?.date??p?.timestamp??p?.time??p?.observed_at??p?.created_at??i;
      return {date:when,balance:Number(balance),equity:Number(equity)};
    }).filter(p=>Number.isFinite(p.balance)&&Number.isFinite(p.equity));
  }

  function normalizeMonthly(data){
    const raw=data.monthly_returns??data.monthly??data.monthly_performance??data.monthly_history??[];
    if(Array.isArray(raw)) return raw.map(r=>({
      period:String(r?.period??r?.month??r?.date??"" ).slice(0,7),
      return_percent:Number(r?.return_percent??r?.return??r?.percentage??r?.percent??r?.value)
    })).filter(r=>/^\d{4}-\d{2}$/.test(r.period)&&Number.isFinite(r.return_percent));
    if(raw&&typeof raw==="object") return Object.entries(raw).map(([period,value])=>({period:String(period).slice(0,7),return_percent:Number(typeof value==="object"?(value.return_percent??value.return??value.value):value)})).filter(r=>/^\d{4}-\d{2}$/.test(r.period)&&Number.isFinite(r.return_percent));
    return [];
  }

  function polylinePath(values,width,height,pad){
    let min=Math.min(...values),max=Math.max(...values);if(max===min){max+=1;min-=1;}
    const x=i=>pad+i*(width-pad*2)/Math.max(1,values.length-1);
    const y=v=>height-pad-(v-min)*(height-pad*2)/(max-min);
    return values.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  }

  function renderBalanceEquity(points){
    const container=document.getElementById("track-chart-container");if(!container)return;
    if(points.length<2){container.className="track-chart-empty";container.textContent="Historical balance/equity points are not yet available from the verified record.";return;}
    const width=1000,height=240,pad=18;
    const all=points.flatMap(p=>[p.balance,p.equity]);let min=Math.min(...all),max=Math.max(...all);if(max===min){max+=1;min-=1;}
    const x=i=>pad+i*(width-pad*2)/(points.length-1),y=v=>height-pad-(v-min)*(height-pad*2)/(max-min);
    const line=key=>points.map((p,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
    container.className="";
    container.innerHTML=`<svg class="track-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Verified balance and equity history"><path d="${line("balance")}" fill="none" stroke="#22d3ee" stroke-width="3" vector-effect="non-scaling-stroke"/><path d="${line("equity")}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><div class="track-chart-legend"><span>Balance ●</span><span>Equity ●</span><span>${points.length} verified historical points</span></div>`;
  }

  function renderGrowth(points){
    const container=document.getElementById("track-growth-container");if(!container)return;
    if(points.length<2||!finite(points[0].balance)||points[0].balance===0){container.className="track-chart-empty";container.textContent="Cumulative growth history will appear when sufficient verified history is available.";return;}
    const base=points[0].balance;
    const growth=points.map(p=>((p.equity/base)-1)*100).filter(Number.isFinite);
    if(growth.length<2){container.textContent="Cumulative growth history is not yet available.";return;}
    const width=1000,height=240,pad=18,path=polylinePath(growth,width,height,pad);
    container.className="";
    container.innerHTML=`<svg class="track-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Verified cumulative growth history"><path d="${path}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"/></svg><div class="track-chart-legend"><span>Cumulative equity growth from first verified balance</span><span>Latest ${signedPercent(growth[growth.length-1])}</span></div>`;
  }

  function renderMonthly(rows){
    const container=document.getElementById("track-monthly");if(!container)return;
    if(!rows.length){container.innerHTML='<span class="track-history-label">No reconciled monthly return rows are available yet.</span>';return;}
    const years=[...new Set(rows.map(r=>r.period.slice(0,4)))].sort();
    const map=new Map(rows.map(r=>[r.period,r.return_percent]));
    const months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    let html='<table class="track-table"><thead><tr><th>Year</th>'+months.map(m=>`<th>${m}</th>`).join("")+'<th>Year Total</th></tr></thead><tbody>';
    years.forEach(year=>{
      const vals=[];html+=`<tr><td>${year}</td>`;
      for(let m=1;m<=12;m++){
        const v=map.get(`${year}-${String(m).padStart(2,"0")}`);
        if(Number.isFinite(v)){vals.push(v/100);html+=`<td class="${v>0?"track-positive":v<0?"track-negative":"track-neutral"}">${signedPercent(v)}</td>`;}else html+='<td>—</td>';
      }
      const annual=vals.length?(vals.reduce((factor,r)=>factor*(1+r),1)-1)*100:NaN;
      html+=`<td class="${annual>0?"track-positive":annual<0?"track-negative":"track-neutral"}">${Number.isFinite(annual)?signedPercent(annual):"—"}</td></tr>`;
    });
    container.innerHTML=html+'</tbody></table>';
  }

  async function refreshVisibility(){
    videoSlot.hidden=true;telemetrySlot.hidden=true;performance.hidden=true;
    try{
      const [b,t]=await Promise.all([
        fetch(`${API}/broadcast/v1/public/status?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}}).then(r=>r.ok?r.json():null),
        fetch(`${API}/connector/v1/public/live?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}}).then(r=>r.ok?r.json():null)
      ]);
      const videoOn=b?.enabled===true,telemetryOn=t?.enabled===true;
      videoSlot.hidden=!videoOn;telemetrySlot.hidden=!telemetryOn;performance.hidden=!(videoOn||telemetryOn);
    }catch(_){videoSlot.hidden=true;telemetrySlot.hidden=true;performance.hidden=true;}
  }

  let loading=false;
  async function loadPerformance(){
    if(loading)return;loading=true;
    try{
      const r=await fetch(`${API}/performance/public-summary?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}});
      if(!r.ok)throw new Error("summary unavailable");
      const d=await r.json();if(d.available===false)throw new Error("record unavailable");
      setText("track-verification",`${String(d.verification_status||"VERIFIED").toUpperCase()} RECORD`);
      setText("track-account",`Bethel Terminal 1 · ${d.account_mask||d.account||"masked"}`);
      setText("track-total-return",signedPercent(d.total_return_percent??d.total_return));
      setText("track-annualized-return",signedPercent(d.annualized_return_percent??d.annualized_return));
      setText("track-max-dd",percent(d.maximum_drawdown_percent??d.max_drawdown_percent??d.maximum_drawdown));
      setText("track-current-dd",percent(d.current_drawdown_percent??d.current_drawdown));
      setText("track-sharpe",number(d.sharpe_ratio??d.sharpe));
      setText("track-sortino",number(d.sortino_ratio??d.sortino));
      setText("track-volatility",percent(d.annualized_volatility_percent??d.volatility_percent??d.annualized_volatility));
      setText("track-winrate",percent(d.win_rate_percent??d.win_rate));
      setText("track-trades",`${Number(d.closed_trades??d.trade_count??d.total_trades??0)} closed trades`);
      setText("track-profit-factor",number(d.profit_factor));
      setText("track-grade",d.performance_grade??d.grade??"—");
      setText("track-risk",`Risk ${d.risk_level??d.risk??"—"}`);
      setText("track-ath",signedPercent(d.all_time_high_return_percent??d.ath_return_percent));
      setText("track-ath-date",date(d.all_time_high_date??d.ath_date));

      const history=normalizeHistory(d),monthly=normalizeMonthly(d);
      const firstDate=d.history_start??history[0]?.date;
      const lastDate=d.history_end??history[history.length-1]?.date;
      const days=d.history_days??d.record_days??history.length;
      setText("track-history-days",`${Number(days||0)} days`);
      setText("track-history-range",`${date(firstDate)} — ${date(lastDate)}`);
      setText("track-methodology",d.methodology||"Read-only signed active-master snapshots and reconciled closed-trade history.");

      renderBalanceEquity(history);
      renderGrowth(history);
      renderMonthly(monthly);
      const loadingEl=document.getElementById("track-loading"),contentEl=document.getElementById("track-content");
      if(loadingEl)loadingEl.hidden=true;if(contentEl)contentEl.hidden=false;
    }catch(_){
      const el=document.getElementById("track-loading");if(el){el.className="track-error";el.textContent="Verified performance history is temporarily unavailable.";}
    }finally{loading=false;}
  }

  refreshVisibility();
  loadPerformance();
  setInterval(refreshVisibility,3000);
  setInterval(loadPerformance,60000);
})();