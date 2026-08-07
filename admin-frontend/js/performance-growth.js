/*
Bethel Trading Technologies
Super Admin Performance Growth Workspace

Admin-only, read-only visualization. Uses protected MT5 performance data for the
active master account. No investor/subscriber or trading-execution behavior is
modified by this file.
*/
(function(){
  "use strict";

  const DAY_MS=86400000;
  const RANGE_MS={"1D":DAY_MS,"1W":7*DAY_MS,"1M":31*DAY_MS,"3M":93*DAY_MS,"6M":186*DAY_MS,"1Y":366*DAY_MS};
  const state={initialized:false,mode:"equity",range:"TOTAL",analytics:{},rows:[],cashFlows:[],series:[],visible:[],geometry:null};

  function waitForRuntime(){
    const started=Date.now();
    const timer=setInterval(()=>{
      if(typeof window.apiGet==="function"&&document.querySelector("#view-analytics")){
        clearInterval(timer);initialize();
      }else if(Date.now()-started>10000){
        clearInterval(timer);console.warn("Bethel Performance Growth: admin runtime unavailable.");
      }
    },100);
  }

  function initialize(){
    if(state.initialized)return;
    state.initialized=true;
    injectStyles();buildPanel();
    document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(loadGrowth,80));
    document.querySelector("#refresh-button")?.addEventListener("click",()=>{
      if(document.querySelector("#view-analytics")?.classList.contains("active"))setTimeout(loadGrowth,120);
    });
    window.addEventListener("resize",()=>{
      if(document.querySelector("#view-analytics")?.classList.contains("active"))drawCurrent();
    });
    if(document.querySelector("#view-analytics")?.classList.contains("active"))loadGrowth();
  }

  function injectStyles(){
    if(document.querySelector("#bethel-performance-growth-style"))return;
    const style=document.createElement("style");
    style.id="bethel-performance-growth-style";
    style.textContent=`
      .bethel-growth-panel{margin-top:18px;padding:0;overflow:hidden;background:rgba(9,18,32,.76)}
      .bethel-growth-titlebar{display:flex;justify-content:space-between;gap:14px;align-items:center;padding:16px 18px;border-bottom:1px solid rgba(148,163,184,.17);background:rgba(3,11,24,.48)}
      .bethel-growth-titlebar h2{margin:0 0 4px;font-size:1.1rem}.bethel-growth-titlebar p{margin:0;color:#94a3b8;font-size:.79rem}
      .bethel-growth-main{display:grid;grid-template-columns:230px minmax(0,1fr);min-height:500px}
      .bethel-growth-sidebar{border-right:1px solid rgba(148,163,184,.17);background:rgba(5,13,25,.52);padding:12px}
      .bethel-growth-side-section{border:1px solid rgba(148,163,184,.15);border-radius:8px;overflow:hidden;margin-bottom:11px;background:rgba(9,19,34,.58)}
      .bethel-growth-side-title{padding:8px 10px;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.055em;color:#cbd5e1;background:rgba(15,28,47,.82);border-bottom:1px solid rgba(148,163,184,.14)}
      .bethel-growth-stat{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 9px;border-bottom:1px solid rgba(148,163,184,.085);font-size:.75rem}
      .bethel-growth-stat:last-child{border-bottom:0}.bethel-growth-stat span{color:#94a3b8}.bethel-growth-stat strong{color:#e5edf7;text-align:right;font-size:.76rem;white-space:nowrap}
      .bethel-growth-stat strong.pos{color:#34d399}.bethel-growth-stat strong.neg{color:#fb7185}.bethel-growth-stat strong.info{color:#60a5fa}
      .bethel-growth-content{padding:12px 14px 14px;min-width:0}
      .bethel-growth-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px;flex-wrap:wrap}
      .bethel-growth-select{appearance:auto;background:#0b1729;color:#e2e8f0;border:1px solid rgba(148,163,184,.25);border-radius:6px;padding:7px 10px;min-width:190px;font-weight:700}
      .bethel-growth-tools{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
      .bethel-growth-ranges{display:flex;gap:3px;padding:3px;border-radius:7px;background:rgba(2,6,23,.48);border:1px solid rgba(148,163,184,.15)}
      .bethel-growth-ranges button{border:0;background:transparent;color:#94a3b8;padding:6px 8px;border-radius:5px;font-size:.7rem;font-weight:800;cursor:pointer}
      .bethel-growth-ranges button.active{background:rgba(59,130,246,.19);color:#e2e8f0;box-shadow:inset 0 0 0 1px rgba(96,165,250,.30)}
      .bethel-growth-ranges button:disabled{opacity:.32;cursor:not-allowed}
      .bethel-growth-refresh{padding:7px 10px}
      .bethel-growth-chart-wrap{position:relative;width:100%;height:405px;overflow:hidden;background:#f8fafc;border:1px solid #cbd5e1;border-radius:4px}
      #bethel-growth-chart{display:block;width:100%;height:100%;cursor:crosshair}
      .bethel-growth-tooltip{position:absolute;display:none;pointer-events:none;z-index:5;min-width:190px;padding:9px 10px;border-radius:7px;background:rgba(4,11,22,.95);border:1px solid rgba(148,163,184,.3);box-shadow:0 10px 26px rgba(0,0,0,.28);font-size:.75rem;color:#cbd5e1}
      .bethel-growth-tooltip strong{display:block;color:#f8fafc;font-size:.82rem;margin-bottom:5px}.bethel-growth-tooltip span{display:block;margin-top:3px}
      .bethel-growth-legend{display:flex;gap:16px;flex-wrap:wrap;margin:8px 2px 0;font-size:.72rem;color:#94a3b8}
      .bethel-growth-legend i{display:inline-block;width:14px;height:3px;margin-right:5px;vertical-align:middle;border-radius:2px}
      .bethel-growth-status{font-size:.71rem;color:#94a3b8;margin-top:6px}
      .bethel-growth-lower{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 14px 14px;margin-left:230px}
      .bethel-growth-mini{border:1px solid rgba(148,163,184,.16);border-radius:8px;background:rgba(6,15,28,.55);overflow:hidden}
      .bethel-growth-mini h3{font-size:.78rem;margin:0;padding:8px 10px;background:rgba(15,28,47,.72);border-bottom:1px solid rgba(148,163,184,.13)}
      .bethel-growth-mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0}.bethel-growth-mini-grid div{padding:9px 10px;border-right:1px solid rgba(148,163,184,.08);border-bottom:1px solid rgba(148,163,184,.08)}
      .bethel-growth-mini-grid small{display:block;color:#94a3b8;font-size:.66rem;text-transform:uppercase}.bethel-growth-mini-grid strong{display:block;margin-top:3px;font-size:.87rem}
      .bethel-growth-note{margin:0 14px 14px 244px;color:#94a3b8;font-size:.72rem;line-height:1.45}
      @media(max-width:980px){.bethel-growth-main{grid-template-columns:1fr}.bethel-growth-sidebar{border-right:0;border-bottom:1px solid rgba(148,163,184,.17);display:grid;grid-template-columns:1fr 1fr;gap:10px}.bethel-growth-side-section{margin:0}.bethel-growth-lower{margin-left:0}.bethel-growth-note{margin-left:14px}}
      @media(max-width:680px){.bethel-growth-sidebar,.bethel-growth-lower{grid-template-columns:1fr}.bethel-growth-chart-wrap{height:330px}.bethel-growth-titlebar{align-items:flex-start;flex-direction:column}.bethel-growth-toolbar{align-items:stretch}.bethel-growth-tools{width:100%}.bethel-growth-ranges{max-width:100%;overflow:auto}}
    `;
    document.head.appendChild(style);
  }

  function buildPanel(){
    const view=document.querySelector("#view-analytics");
    if(!view||document.querySelector("#bethel-performance-growth"))return;
    const panel=document.createElement("article");
    panel.id="bethel-performance-growth";panel.className="panel bethel-growth-panel";
    panel.innerHTML=`
      <div class="bethel-growth-titlebar">
        <div><h2>Account Growth & Performance</h2><p>Professional account history for the currently active master account.</p></div>
        <button id="bethel-growth-reload" class="bethel-growth-refresh" type="button">Refresh chart</button>
      </div>
      <div class="bethel-growth-main">
        <aside class="bethel-growth-sidebar">
          <section class="bethel-growth-side-section"><div class="bethel-growth-side-title">Account</div><div id="bethel-growth-account-stats"></div></section>
          <section class="bethel-growth-side-section"><div class="bethel-growth-side-title">Performance</div><div id="bethel-growth-performance-stats"></div></section>
          <section class="bethel-growth-side-section"><div class="bethel-growth-side-title">Risk</div><div id="bethel-growth-risk-stats"></div></section>
        </aside>
        <div class="bethel-growth-content">
          <div class="bethel-growth-toolbar">
            <select id="bethel-growth-mode" class="bethel-growth-select" aria-label="Chart type">
              <option value="equity">Balance & Equity</option>
              <option value="return">Cash-flow-adjusted Return %</option>
            </select>
            <div class="bethel-growth-tools">
              <div class="bethel-growth-ranges" aria-label="Chart range">
                <button type="button" data-growth-range="TOTAL" class="active">TOTAL</button><button type="button" data-growth-range="1Y">1Y</button><button type="button" data-growth-range="6M">6M</button><button type="button" data-growth-range="3M">3M</button><button type="button" data-growth-range="1M">1M</button><button type="button" data-growth-range="1W">1W</button><button type="button" data-growth-range="1D">1D</button>
              </div>
            </div>
          </div>
          <div class="bethel-growth-chart-wrap"><canvas id="bethel-growth-chart" aria-label="Bethel performance history chart"></canvas><div id="bethel-growth-tooltip" class="bethel-growth-tooltip"></div></div>
          <div id="bethel-growth-legend" class="bethel-growth-legend"></div>
          <div id="bethel-growth-status" class="bethel-growth-status"></div>
        </div>
      </div>
      <div class="bethel-growth-lower">
        <section class="bethel-growth-mini"><h3>Trading Statistics</h3><div id="bethel-growth-trading-mini" class="bethel-growth-mini-grid"></div></section>
        <section class="bethel-growth-mini"><h3>Account History</h3><div id="bethel-growth-history-mini" class="bethel-growth-mini-grid"></div></section>
      </div>
      <p class="bethel-growth-note">Balance and equity are actual signed MT5 snapshot values. Return mode neutralizes recorded deposits/withdrawals and uses the same active-master account history window as Bethel analytics. No synthetic performance observations are generated.</p>`;
    const risk=document.querySelector("#bethel-risk-monitor");if(risk)view.insertBefore(panel,risk);else view.appendChild(panel);

    document.querySelector("#bethel-growth-reload")?.addEventListener("click",loadGrowth);
    document.querySelector("#bethel-growth-mode")?.addEventListener("change",event=>{state.mode=event.target.value;updateLegend();applyRange();});
    panel.querySelectorAll("[data-growth-range]").forEach(button=>button.addEventListener("click",()=>{
      state.range=button.dataset.growthRange;panel.querySelectorAll("[data-growth-range]").forEach(b=>b.classList.toggle("active",b===button));applyRange();
    }));
    const canvas=panel.querySelector("#bethel-growth-chart");canvas.addEventListener("mousemove",handleHover);canvas.addEventListener("mouseleave",()=>{hideTooltip();drawCurrent();});
    updateLegend();
  }

  async function loadGrowth(){
    buildPanel();const button=document.querySelector("#bethel-growth-reload");if(button){button.disabled=true;button.textContent="Refreshing…";}setStatus("Loading signed MT5 history…");
    try{
      const [analytics,historyResponse,audit]=await Promise.all([
        window.apiGet("/performance/analytics"),window.apiGet("/performance/equity-history"),window.apiGet("/performance/analytics-fxblue-banked-return-preview").catch(()=>null)
      ]);
      const account=String(analytics?.master_account||"").trim(),historyDays=Number(analytics?.history_days);
      let rows=(historyResponse?.history||[]).filter(row=>!account||String(row.account_number||"").trim()===account).map(row=>({...row,_at:parseDate(row.timestamp)})).filter(row=>row._at&&Number.isFinite(Number(row.equity))&&Number(row.equity)>0).sort((a,b)=>a._at-b._at);
      if(rows.length&&Number.isFinite(historyDays)&&historyDays>0){const end=rows[rows.length-1]._at,start=new Date(end.getTime()-historyDays*DAY_MS);rows=rows.filter(row=>row._at>=start&&row._at<=end);}
      state.analytics=analytics||{};state.rows=rows;state.cashFlows=normalizeCashFlows(audit?.cash_flows||[]);state.series=buildSeries(rows,state.cashFlows);
      renderAllStats();updateRangeAvailability();applyRange();
      setStatus(rows.length?`${rows.length.toLocaleString()} signed MT5 snapshots · latest ${formatDateTime(rows[rows.length-1]._at)}`:"No MT5 snapshots available in the account-history window.");
    }catch(error){state.rows=[];state.series=[];state.visible=[];setStatus(`Performance chart unavailable: ${error?.message||"unable to load history"}`);renderAllStats();drawCurrent();}
    finally{if(button){button.disabled=false;button.textContent="Refresh chart";}}
  }

  function normalizeCashFlows(flows){return flows.map(flow=>({at:parseDate(flow.occurred_at),amount:Number(flow.amount||0)})).filter(flow=>flow.at&&Number.isFinite(flow.amount)).sort((a,b)=>a.at-b.at);}
  function buildSeries(rows,cashFlows){
    if(!rows.length)return[];const out=[];let factor=1;out.push(pointFromRow(rows[0],0));
    for(let i=1;i<rows.length;i++){
      const prev=rows[i-1],curr=rows[i],prevEq=Number(prev.equity),currEq=Number(curr.equity);
      const externalFlow=cashFlows.reduce((sum,flow)=>flow.at>prev._at&&flow.at<=curr._at?sum+flow.amount:sum,0);
      if(prevEq>0){const periodFactor=(currEq-externalFlow)/prevEq;if(Number.isFinite(periodFactor)&&periodFactor>0)factor*=periodFactor;}
      out.push(pointFromRow(curr,(factor-1)*100));
    }return out;
  }
  function pointFromRow(row,returnPct){return{at:row._at,equity:Number(row.equity),balance:Number(row.balance||0),returnPct:Number(returnPct)};}

  function applyRange(){
    const full=state.series;if(!full.length){state.visible=[];drawCurrent();return;}
    if(state.range==="TOTAL")state.visible=full;else{const end=full[full.length-1].at.getTime(),start=end-(RANGE_MS[state.range]||Infinity);state.visible=full.filter(p=>p.at.getTime()>=start);if(!state.visible.length)state.visible=[full[full.length-1]];}
    renderRangeStatus();drawCurrent();
  }
  function updateRangeAvailability(){
    const panel=document.querySelector("#bethel-performance-growth");if(!panel||!state.series.length)return;const span=state.series[state.series.length-1].at-state.series[0].at;
    panel.querySelectorAll("[data-growth-range]").forEach(button=>{const range=button.dataset.growthRange;button.disabled=range!=="TOTAL"&&span<Math.min(RANGE_MS[range]||0,DAY_MS*.75);});
  }

  function renderAllStats(){
    const a=state.analytics||{},rows=state.rows,last=rows[rows.length-1]||{};
    fill("#bethel-growth-account-stats",[
      stat("Master",a.master_account||"—","info"),stat("Balance",money(a.current_balance??last.balance)),stat("Equity",money(a.current_equity??last.equity)),stat("Floating P/L",money(a.floating_profit_loss),numClass(a.floating_profit_loss)),stat("Closed profit",money(a.closed_profit),numClass(a.closed_profit)),stat("History",Number.isFinite(Number(a.history_days))?`${Number(a.history_days).toFixed(1)} days`:"—")
    ]);
    fill("#bethel-growth-performance-stats",[
      stat("Total return",signedPct(a.total_return_percent),numClass(a.total_return_percent)),stat("Monthly",signedPct(a.monthly_return_percent),numClass(a.monthly_return_percent)),stat("Weekly",signedPct(a.weekly_return_percent),numClass(a.weekly_return_percent)),stat("Daily",signedPct(a.daily_return_percent),numClass(a.daily_return_percent)),stat("Profit factor",fmt(a.profit_factor)),stat("Win rate",pct(a.win_rate))
    ]);
    fill("#bethel-growth-risk-stats",[
      stat("Max drawdown",pct(a.maximum_drawdown_percent),"neg"),stat("VaR 95%",a.var_status==="available"?pct(a.value_at_risk_95_percent):"Building"),stat("Recovery",fmt(a.recovery_factor)),stat("Sharpe",fmt(a.sharpe_ratio)),stat("Sortino",fmt(a.sortino_ratio)),stat("Risk level",a.risk_level||"—",String(a.risk_level).toUpperCase()==="HIGH"?"neg":"info")
    ]);
    fillMini("#bethel-growth-trading-mini",[["Trades",a.total_trades],["Winning",a.winning_trades],["Losing",a.losing_trades],["Avg win",money(a.average_win)],["Avg loss",money(a.average_loss)],["Expectancy",money(a.expectancy)]]);
    fillMini("#bethel-growth-history-mini",[["Start",rows.length?formatDate(rows[0]._at):"—"],["End",rows.length?formatDate(rows[rows.length-1]._at):"—"],["Snapshots",rows.length.toLocaleString()],["Deposits",money(a.deposits)],["Withdrawals",money(a.withdrawals)],["Cash-flow events",a.cash_flow_events??0]]);
  }
  function stat(label,value,cls=""){return `<div class="bethel-growth-stat"><span>${escapeText(label)}</span><strong class="${cls}">${escapeText(value)}</strong></div>`;}
  function fill(selector,html){const el=document.querySelector(selector);if(el)el.innerHTML=html.join("");}
  function fillMini(selector,items){const el=document.querySelector(selector);if(el)el.innerHTML=items.map(([l,v])=>`<div><small>${escapeText(l)}</small><strong>${escapeText(v??"—")}</strong></div>`).join("");}

  function renderRangeStatus(){
    if(!state.visible.length)return;const first=state.visible[0],last=state.visible[state.visible.length-1];
    if(state.mode==="return"){const s=1+first.returnPct/100,e=1+last.returnPct/100,r=s>0?((e/s)-1)*100:0;setStatus(`${state.range} · ${formatDate(first.at)} → ${formatDate(last.at)} · Return ${r>=0?"+":""}${r.toFixed(2)}% · ${state.visible.length.toLocaleString()} points`);}else setStatus(`${state.range} · ${formatDate(first.at)} → ${formatDate(last.at)} · ${state.visible.length.toLocaleString()} actual MT5 snapshots`);
  }
  function updateLegend(){
    const el=document.querySelector("#bethel-growth-legend");if(!el)return;
    el.innerHTML=state.mode==="return"?'<span><i style="background:#2563eb"></i>Cash-flow-adjusted return %</span>':'<span><i style="background:#2563eb"></i>Equity</span><span><i style="background:#ef4444"></i>Balance</span>';
  }

  function drawCurrent(crosshairIndex=null){
    const canvas=document.querySelector("#bethel-growth-chart");if(!canvas)return;const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,width=Math.max(560,Math.floor(rect.width||920)),height=Math.max(300,Math.floor(rect.height||405));
    canvas.width=width*dpr;canvas.height=height*dpr;const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);ctx.fillStyle="#f8fafc";ctx.fillRect(0,0,width,height);ctx.font="11px Arial, sans-serif";
    const series=state.visible;if(!series.length){ctx.fillStyle="#64748b";ctx.fillText("No account-history data available for this period.",24,40);state.geometry=null;return;}
    const pad={l:66,r:18,t:25,b:47},plotW=width-pad.l-pad.r,plotH=height-pad.t-pad.b,times=series.map(p=>p.at.getTime()),minTime=Math.min(...times),maxTime=Math.max(...times);
    const vals=state.mode==="return"?series.map(p=>p.returnPct):series.flatMap(p=>[p.equity,p.balance]);let min=Math.min(...vals.filter(Number.isFinite)),max=Math.max(...vals.filter(Number.isFinite));if(state.mode==="return"){min=Math.min(min,0);max=Math.max(max,0);}if(max===min){max+=1;min-=1;}const margin=(max-min)*.08||1;min-=margin;max+=margin;
    const xTime=t=>pad.l+(maxTime===minTime?plotW/2:((t-minTime)/(maxTime-minTime))*plotW),yVal=v=>pad.t+((max-v)/(max-min))*plotH,x=i=>xTime(times[i]);
    drawGrid(ctx,{width,height,pad,plotW,plotH,min,max,minTime,maxTime,xTime,yVal});
    if(state.mode==="return"){const zy=yVal(0);drawFilledLine(ctx,series,p=>p.returnPct,x,yVal,zy,"#2563eb","rgba(37,99,235,.16)");}
    else{drawFilledLine(ctx,series,p=>p.equity,x,yVal,height-pad.b,"#2563eb","rgba(37,99,235,.13)");drawFilledLine(ctx,series,p=>p.balance,x,yVal,height-pad.b,"#ef4444","rgba(239,68,68,.10)");}
    if(Number.isInteger(crosshairIndex)&&series[crosshairIndex]){const cx=x(crosshairIndex);ctx.strokeStyle="rgba(15,23,42,.48)";ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(cx,pad.t);ctx.lineTo(cx,height-pad.b);ctx.stroke();ctx.setLineDash([]);const p=series[crosshairIndex],v=state.mode==="return"?p.returnPct:p.equity;ctx.fillStyle="#0f172a";ctx.beginPath();ctx.arc(cx,yVal(v),3.6,0,Math.PI*2);ctx.fill();}
    state.geometry={width,height,pad,plotW,times,minTime,maxTime,series};
  }

  function drawGrid(ctx,g){
    const h=5,v=7;ctx.lineWidth=1;
    for(let i=0;i<=h;i++){const r=i/h,y=g.pad.t+g.plotH*r;ctx.strokeStyle="#d9e1ea";ctx.beginPath();ctx.moveTo(g.pad.l,y);ctx.lineTo(g.width-g.pad.r,y);ctx.stroke();const val=g.max-(g.max-g.min)*r;ctx.fillStyle="#64748b";ctx.textAlign="right";ctx.textBaseline="middle";ctx.fillText(state.mode==="return"?`${val.toFixed(Math.abs(val)<10?2:1)}%`:compactMoney(val),g.pad.l-8,y);}
    for(let i=0;i<=v;i++){const r=i/v,t=g.minTime+(g.maxTime-g.minTime)*r,x=g.xTime(t);ctx.strokeStyle="#e8edf3";ctx.beginPath();ctx.moveTo(x,g.pad.t);ctx.lineTo(x,g.height-g.pad.b);ctx.stroke();ctx.fillStyle="#64748b";ctx.textAlign=i===0?"left":i===v?"right":"center";ctx.textBaseline="top";ctx.fillText(formatAxisDate(new Date(t),g.maxTime-g.minTime),x,g.height-g.pad.b+10);}ctx.textAlign="left";ctx.textBaseline="alphabetic";
  }
  function drawFilledLine(ctx,series,getValue,x,y,baseY,lineColor,fillColor){
    if(series.length<1)return;ctx.beginPath();ctx.moveTo(x(0),baseY);series.forEach((p,i)=>ctx.lineTo(x(i),y(Number(getValue(p)))));ctx.lineTo(x(series.length-1),baseY);ctx.closePath();ctx.fillStyle=fillColor;ctx.fill();ctx.beginPath();series.forEach((p,i)=>{const xx=x(i),yy=y(Number(getValue(p)));if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy);});ctx.strokeStyle=lineColor;ctx.lineWidth=1.8;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();
  }

  function handleHover(event){
    const g=state.geometry;if(!g||!g.series.length)return;const rect=event.currentTarget.getBoundingClientRect(),mx=event.clientX-rect.left;if(mx<g.pad.l||mx>g.width-g.pad.r){hideTooltip();drawCurrent();return;}const target=g.minTime+((mx-g.pad.l)/g.plotW)*(g.maxTime-g.minTime);let index=0,best=Infinity;g.times.forEach((t,i)=>{const d=Math.abs(t-target);if(d<best){best=d;index=i;}});drawCurrent(index);showTooltip(g.series[index],mx,event.clientY-rect.top,rect.width);
  }
  function showTooltip(p,x,y,width){const tip=document.querySelector("#bethel-growth-tooltip");if(!tip)return;tip.innerHTML=`<strong>${escapeText(formatDateTime(p.at))}</strong><span>Balance: ${escapeText(money(p.balance))}</span><span>Equity: ${escapeText(money(p.equity))}</span><span>Return: ${p.returnPct>=0?"+":""}${p.returnPct.toFixed(2)}%</span>`;tip.style.display="block";tip.style.left=`${Math.min(Math.max(8,x+14),Math.max(8,width-210))}px`;tip.style.top=`${Math.max(8,y-28)}px`;}
  function hideTooltip(){const tip=document.querySelector("#bethel-growth-tooltip");if(tip)tip.style.display="none";}

  function setStatus(text){const el=document.querySelector("#bethel-growth-status");if(el)el.textContent=text;}
  function normalizeTimestamp(v){const t=String(v||"").trim();if(!t)return t;if(/[zZ]$|[+-]\d\d:?\d\d$/.test(t))return t;return t.replace(" ","T")+"Z";}
  function parseDate(v){if(!v)return null;const d=new Date(normalizeTimestamp(v));return Number.isNaN(d.getTime())?null:d;}
  function formatDate(d){return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});}
  function formatDateTime(d){return d.toLocaleString("en-GB",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"UTC"})+" UTC";}
  function formatAxisDate(d,span){if(span<=2*DAY_MS)return d.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",timeZone:"UTC"});if(span<=62*DAY_MS)return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",timeZone:"UTC"});return d.toLocaleDateString("en-GB",{month:"short",year:"2-digit",timeZone:"UTC"});}
  function money(v){const n=Number(v);if(!Number.isFinite(n))return"—";try{return new Intl.NumberFormat("en",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(n);}catch{return n.toFixed(2);}}
  function compactMoney(v){const n=Number(v);return Number.isFinite(n)?"$"+new Intl.NumberFormat("en",{notation:"compact",maximumFractionDigits:1}).format(n):"—";}
  function pct(v){const n=Number(v);return Number.isFinite(n)?`${n.toFixed(2)}%`:"—";}
  function signedPct(v){const n=Number(v);return Number.isFinite(n)?`${n>=0?"+":""}${n.toFixed(2)}%`:"—";}
  function fmt(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(2):"—";}
  function numClass(v){const n=Number(v);return !Number.isFinite(n)?"":n>0?"pos":n<0?"neg":"";}
  function escapeText(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

  waitForRuntime();
})();
