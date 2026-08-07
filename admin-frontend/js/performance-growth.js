/*
Bethel Trading Technologies
Super Admin Performance Growth Chart

Read-only visualization. The currently active master is resolved dynamically by
the backend. Verified MT5 ledger history extends the balance curve; equity is
plotted only from actual stored EquitySnapshot observations. No account values,
dates, balances, returns or master account numbers are hard-coded.
*/
(function(){
  "use strict";
  const DAY=86400000;
  const RANGES={TOTAL:null,"1Y":366*DAY,"6M":186*DAY,"3M":93*DAY,"1M":31*DAY,"1W":7*DAY,"1D":DAY};
  const state={ready:false,mode:"account",range:"TOTAL",analytics:{},snapshots:[],ledger:[],returns:[],visible:{snapshots:[],ledger:[],returns:[]},geometry:null};

  function boot(){
    const started=Date.now();
    const timer=setInterval(()=>{
      if(typeof window.apiGet==="function"&&document.querySelector("#view-analytics")){clearInterval(timer);init();}
      else if(Date.now()-started>10000){clearInterval(timer);console.warn("Bethel performance chart runtime unavailable");}
    },100);
  }

  function init(){
    if(state.ready)return;state.ready=true;styles();panel();
    document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(load,80));
    document.querySelector("#refresh-button")?.addEventListener("click",()=>{if(document.querySelector("#view-analytics")?.classList.contains("active"))setTimeout(load,100);});
    window.addEventListener("resize",()=>draw());
    if(document.querySelector("#view-analytics")?.classList.contains("active"))load();
  }

  function styles(){
    if(document.querySelector("#bethel-performance-growth-style"))return;
    const s=document.createElement("style");s.id="bethel-performance-growth-style";
    s.textContent=`
      .bethel-growth-panel{margin-top:18px}.bethel-growth-title{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px}
      .bethel-growth-title h2{margin:0 0 4px}.bethel-growth-title p{margin:0;color:#94a3b8}.bethel-growth-shell{display:grid;grid-template-columns:minmax(210px,250px) minmax(0,1fr);gap:14px}
      .bethel-growth-side{display:flex;flex-direction:column;gap:10px}.bethel-growth-box{border:1px solid rgba(148,163,184,.15);background:rgba(8,18,33,.64);border-radius:11px;padding:11px 12px}
      .bethel-growth-box h3{font-size:.83rem;margin:0 0 8px;color:#e2e8f0}.bethel-growth-row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid rgba(148,163,184,.08);font-size:.76rem}
      .bethel-growth-row:last-child{border-bottom:0}.bethel-growth-row span{color:#94a3b8}.bethel-growth-row strong{color:#f8fafc;text-align:right}.bethel-growth-main{min-width:0}
      .bethel-growth-controls{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:8px}.bethel-growth-tabs,.bethel-growth-ranges{display:flex;gap:4px;padding:4px;border-radius:9px;background:rgba(2,6,23,.55);border:1px solid rgba(148,163,184,.13);overflow:auto}
      .bethel-growth-tabs button,.bethel-growth-ranges button{border:0;background:transparent;color:#94a3b8;padding:7px 9px;border-radius:6px;font-size:.74rem;font-weight:700;cursor:pointer;white-space:nowrap}.bethel-growth-tabs button.active,.bethel-growth-ranges button.active{background:rgba(56,189,248,.14);color:#f8fafc;box-shadow:inset 0 0 0 1px rgba(56,189,248,.25)}
      .bethel-growth-tabs button:disabled,.bethel-growth-ranges button:disabled{opacity:.35;cursor:not-allowed}.bethel-growth-chart-wrap{position:relative;overflow:hidden;border-radius:10px;border:1px solid rgba(148,163,184,.14);background:linear-gradient(180deg,rgba(5,13,27,.87),rgba(2,6,23,.68))}
      #bethel-growth-chart{display:block;width:100%;height:420px;cursor:crosshair}.bethel-growth-tooltip{position:absolute;display:none;z-index:5;pointer-events:none;min-width:185px;padding:9px 10px;border-radius:8px;background:rgba(2,6,23,.96);border:1px solid rgba(148,163,184,.25);box-shadow:0 10px 28px rgba(0,0,0,.32);font-size:.75rem;color:#cbd5e1}
      .bethel-growth-tooltip strong{display:block;color:#fff;margin-bottom:5px}.bethel-growth-tooltip span{display:block;margin-top:3px}.bethel-growth-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:.75rem;color:#cbd5e1}.bethel-growth-key:before{content:"";display:inline-block;width:16px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle;background:currentColor}
      .bethel-growth-status{margin-top:8px;font-size:.74rem;color:#94a3b8}.bethel-growth-status.ok{color:#86efac}.bethel-growth-status.bad{color:#fca5a5}@media(max-width:980px){.bethel-growth-shell{grid-template-columns:1fr}.bethel-growth-side{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}#bethel-growth-chart{height:340px}}
    `;document.head.appendChild(s);
  }

  function panel(){
    const view=document.querySelector("#view-analytics");if(!view||document.querySelector("#bethel-performance-growth"))return;
    const el=document.createElement("article");el.id="bethel-performance-growth";el.className="panel bethel-growth-panel";
    el.innerHTML=`
      <div class="bethel-growth-title"><div><h2>Account Growth & Performance</h2><p>Live performance history for the currently active MT5 master account.</p></div><button id="bethel-growth-reload" type="button">Refresh chart</button></div>
      <div class="bethel-growth-shell"><aside class="bethel-growth-side">
        <div class="bethel-growth-box"><h3>Account</h3><div id="bethel-growth-account"></div></div>
        <div class="bethel-growth-box"><h3>Performance</h3><div id="bethel-growth-performance"></div></div>
        <div class="bethel-growth-box"><h3>Risk</h3><div id="bethel-growth-risk"></div></div>
      </aside><section class="bethel-growth-main">
        <div class="bethel-growth-controls"><div class="bethel-growth-tabs"><button type="button" data-growth-mode="account" class="active">Balance & Equity</button><button type="button" data-growth-mode="return">Return %</button></div>
        <div class="bethel-growth-ranges">${Object.keys(RANGES).map(r=>`<button type="button" data-growth-range="${r}" class="${r==="TOTAL"?"active":""}">${r}</button>`).join("")}</div></div>
        <div class="bethel-growth-chart-wrap"><canvas id="bethel-growth-chart"></canvas><div id="bethel-growth-tooltip" class="bethel-growth-tooltip"></div></div>
        <div id="bethel-growth-legend" class="bethel-growth-legend"></div><div id="bethel-growth-status" class="bethel-growth-status"></div>
      </section></div>`;
    const risk=document.querySelector("#bethel-risk-monitor");risk?view.insertBefore(el,risk):view.appendChild(el);
    document.querySelector("#bethel-growth-reload")?.addEventListener("click",load);
    el.querySelectorAll("[data-growth-mode]").forEach(b=>b.addEventListener("click",()=>{state.mode=b.dataset.growthMode;el.querySelectorAll("[data-growth-mode]").forEach(x=>x.classList.toggle("active",x===b));applyRange();}));
    el.querySelectorAll("[data-growth-range]").forEach(b=>b.addEventListener("click",()=>{state.range=b.dataset.growthRange;el.querySelectorAll("[data-growth-range]").forEach(x=>x.classList.toggle("active",x===b));applyRange();}));
    const c=el.querySelector("#bethel-growth-chart");c.addEventListener("mousemove",hover);c.addEventListener("mouseleave",()=>{hideTip();draw();});
  }

  async function load(){
    panel();const button=document.querySelector("#bethel-growth-reload");if(button){button.disabled=true;button.textContent="Refreshing…";}status("Refreshing live master-account history…","");
    try{
      const [analytics,history,trades,audit]=await Promise.all([
        window.apiGet("/performance/analytics"),window.apiGet("/performance/equity-history"),window.apiGet("/performance/trades"),window.apiGet("/performance/analytics-fxblue-banked-return-preview").catch(()=>null)
      ]);
      const account=String(analytics?.master_account||"").trim();if(!account)throw new Error("No active master account resolved");
      if(trades?.master_account&&String(trades.master_account).trim()!==account)throw new Error("Performance sources are not synchronized to the same master account");
      state.analytics=analytics||{};
      state.snapshots=(history?.history||[]).filter(r=>String(r.account_number||"").trim()===account).map(r=>({at:date(r.timestamp),balance:Number(r.balance),equity:Number(r.equity),profit:Number(r.profit||0)})).filter(r=>r.at&&Number.isFinite(r.balance)&&Number.isFinite(r.equity)&&r.equity>0).sort((a,b)=>a.at-b.at);
      const ledger=trades?.ledger_history||{};
      state.ledger=ledger.status==="verified"?(ledger.balance_history||[]).map(r=>({at:date(r.timestamp),balance:Number(r.balance),event:r.event,amount:Number(r.amount||0)})).filter(r=>r.at&&Number.isFinite(r.balance)).sort((a,b)=>a.at-b.at):[];
      state.returns=returnSeries(state.snapshots,normalizeFlows(audit?.cash_flows||[]));
      renderSide(account);rangeAvailability();applyRange();status(`Live master ${account} · ${state.snapshots.length.toLocaleString()} MT5 observations`,"ok");
    }catch(e){state.snapshots=[];state.ledger=[];state.returns=[];state.visible={snapshots:[],ledger:[],returns:[]};status(e?.message||"Unable to load performance history","bad");draw();}
    finally{if(button){button.disabled=false;button.textContent="Refresh chart";}}
  }

  function normalizeFlows(flows){return flows.map(f=>({at:date(f.occurred_at),amount:Number(f.amount||0)})).filter(f=>f.at&&Number.isFinite(f.amount)).sort((a,b)=>a.at-b.at);}
  function returnSeries(rows,flows){if(!rows.length)return[];let factor=1;const out=[{...rows[0],returnPct:0}];for(let i=1;i<rows.length;i++){const p=rows[i-1],c=rows[i],flow=flows.reduce((s,f)=>f.at>p.at&&f.at<=c.at?s+f.amount:s,0);if(p.equity>0){const q=(c.equity-flow)/p.equity;if(Number.isFinite(q)&&q>0)factor*=q;}out.push({...c,returnPct:(factor-1)*100});}return out;}

  function renderSide(account){
    const a=state.analytics,s=state.snapshots,last=s[s.length-1];
    setRows("bethel-growth-account",[["Master account",account],["Balance",last?money(last.balance):money(a.current_balance)],["Equity",last?money(last.equity):money(a.current_equity)],["History",num(a.history_days,1," days")],["Trades",num(a.total_trades,0)]]);
    setRows("bethel-growth-performance",[["Total return",pctOr(a.total_return_percent)],["Monthly",pctOr(a.monthly_return_percent)],["Weekly",pctOr(a.weekly_return_percent)],["Daily",pctOr(a.daily_return_percent)],["Profit factor",num(a.profit_factor,2)],["Win rate",pctOr(a.win_rate)]]);
    setRows("bethel-growth-risk",[["Max drawdown",pctOr(a.maximum_drawdown_percent)],["VaR 95%",pctOr(a.value_at_risk_95_percent)],["Sharpe",num(a.sharpe_ratio,2)],["Sortino",num(a.sortino_ratio,2)],["Risk level",a.risk_level||"—"],["Grade",a.performance_grade||"—"]]);
  }
  function setRows(id,rows){const e=document.getElementById(id);if(e)e.innerHTML=rows.map(([k,v])=>`<div class="bethel-growth-row"><span>${esc(k)}</span><strong>${esc(v??"—")}</strong></div>`).join("");}

  function rangeAvailability(){const all=[...state.snapshots.map(x=>x.at),...state.ledger.map(x=>x.at)].sort((a,b)=>a-b);if(!all.length)return;const span=all[all.length-1]-all[0];document.querySelectorAll("[data-growth-range]").forEach(b=>{const ms=RANGES[b.dataset.growthRange];b.disabled=ms!==null&&span<ms*.75;});}
  function applyRange(){const ends=[...state.snapshots.map(x=>x.at.getTime()),...state.ledger.map(x=>x.at.getTime())];if(!ends.length){state.visible={snapshots:[],ledger:[],returns:[]};draw();return;}const end=Math.max(...ends),ms=RANGES[state.range],start=ms===null?-Infinity:end-ms;state.visible={snapshots:state.snapshots.filter(x=>x.at.getTime()>=start),ledger:state.ledger.filter(x=>x.at.getTime()>=start),returns:state.returns.filter(x=>x.at.getTime()>=start)};draw();legend();}
  function legend(){const e=document.getElementById("bethel-growth-legend");if(!e)return;e.innerHTML=state.mode==="return"?'<span class="bethel-growth-key" style="color:#38bdf8">Cash-flow-adjusted return %</span>':'<span class="bethel-growth-key" style="color:#ef4444">Balance</span><span class="bethel-growth-key" style="color:#38bdf8">Equity</span>';}

  function draw(){
    const canvas=document.getElementById("bethel-growth-chart");if(!canvas)return;const r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=Math.max(520,Math.floor(r.width||900)),h=Math.max(300,Math.floor(r.height||420));canvas.width=w*dpr;canvas.height=h*dpr;
    const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);ctx.font="12px system-ui";const ss=state.visible.snapshots,ll=state.visible.ledger,rr=state.visible.returns;
    const chosen=state.mode==="return"?rr:(ss.length||ll.length?[1]:[]);if(!chosen.length){ctx.fillStyle="#94a3b8";ctx.fillText("Performance history is loading for the active master account.",24,40);state.geometry=null;return;}
    const times=state.mode==="return"?rr.map(x=>x.at.getTime()):[...ss.map(x=>x.at.getTime()),...ll.map(x=>x.at.getTime())],minT=Math.min(...times),maxT=Math.max(...times),pad={l:78,r:24,t:22,b:46},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
    let vals=state.mode==="return"?rr.map(x=>x.returnPct):[...ss.flatMap(x=>[x.balance,x.equity]),...ll.map(x=>x.balance)];vals=vals.filter(Number.isFinite);let min=Math.min(...vals),max=Math.max(...vals);if(state.mode==="return"){min=Math.min(min,0);max=Math.max(max,0);}if(max===min){max+=1;min-=1;}const extra=(max-min)*.1||1;min-=extra;max+=extra;
    const xf=t=>pad.l+(maxT===minT?pw/2:((t-minT)/(maxT-minT))*pw),yf=v=>pad.t+((max-v)/(max-min))*ph;grid(ctx,w,h,pad,pw,ph,min,max,minT,maxT,xf);
    if(state.mode==="return"){const zero=yf(0);ctx.strokeStyle="rgba(226,232,240,.28)";ctx.beginPath();ctx.moveTo(pad.l,zero);ctx.lineTo(w-pad.r,zero);ctx.stroke();line(ctx,rr,x=>x.returnPct,xf,yf,"#38bdf8",2.4);}else{if(ll.length)line(ctx,ll,x=>x.balance,xf,yf,"#ef4444",2.1);else if(ss.length)line(ctx,ss,x=>x.balance,xf,yf,"#ef4444",2.1);if(ss.length)line(ctx,ss,x=>x.equity,xf,yf,"#38bdf8",2.5);}
    state.geometry={w,h,pad,pw,ph,minT,maxT,xf,yf};
  }
  function grid(ctx,w,h,pad,pw,ph,min,max,minT,maxT,xf){ctx.lineWidth=1;for(let i=0;i<=5;i++){const y=pad.t+ph*i/5;ctx.strokeStyle="rgba(148,163,184,.13)";ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();const v=max-(max-min)*i/5;ctx.fillStyle="#94a3b8";ctx.textAlign="right";ctx.textBaseline="middle";ctx.fillText(state.mode==="return"?`${v.toFixed(Math.abs(v)<10?2:1)}%`:compact(v),pad.l-9,y);}for(let i=0;i<=6;i++){const t=minT+(maxT-minT)*i/6,x=xf(t);ctx.strokeStyle="rgba(148,163,184,.09)";ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();ctx.fillStyle="#94a3b8";ctx.textAlign=i===0?"left":i===6?"right":"center";ctx.textBaseline="top";ctx.fillText(axisDate(new Date(t),maxT-minT),x,h-pad.b+11);}ctx.textAlign="left";ctx.textBaseline="alphabetic";}
  function line(ctx,arr,get,xf,yf,color,width){ctx.beginPath();let started=false;arr.forEach(p=>{const v=Number(get(p));if(!Number.isFinite(v))return;const x=xf(p.at.getTime()),y=yf(v);if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);});ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();}

  function hover(ev){const g=state.geometry;if(!g)return;const rect=ev.currentTarget.getBoundingClientRect(),mx=ev.clientX-rect.left;if(mx<g.pad.l||mx>g.w-g.pad.r){hideTip();return;}const target=g.minT+((mx-g.pad.l)/g.pw)*(g.maxT-g.minT);const arr=state.mode==="return"?state.visible.returns:state.visible.snapshots;if(!arr.length)return;let best=arr[0],dist=Infinity;arr.forEach(p=>{const d=Math.abs(p.at.getTime()-target);if(d<dist){best=p;dist=d;}});const tip=document.getElementById("bethel-growth-tooltip");if(!tip)return;tip.innerHTML=state.mode==="return"?`<strong>${esc(fmtTime(best.at))}</strong><span>Return: ${best.returnPct>=0?"+":""}${best.returnPct.toFixed(2)}%</span><span>Equity: ${esc(money(best.equity))}</span><span>Balance: ${esc(money(best.balance))}</span>`:`<strong>${esc(fmtTime(best.at))}</strong><span>Equity: ${esc(money(best.equity))}</span><span>Balance: ${esc(money(best.balance))}</span>`;tip.style.display="block";tip.style.left=`${Math.min(Math.max(8,mx+12),Math.max(8,rect.width-205))}px`;tip.style.top=`${Math.max(8,ev.clientY-rect.top-20)}px`;}
  function hideTip(){const x=document.getElementById("bethel-growth-tooltip");if(x)x.style.display="none";}
  function status(text,kind){const e=document.getElementById("bethel-growth-status");if(e){e.textContent=text;e.className=`bethel-growth-status ${kind||""}`;}}
  function date(v){if(!v)return null;const t=String(v).trim(),iso=/[zZ]$|[+-]\d\d:?\d\d$/.test(t)?t:t.replace(" ","T")+"Z",d=new Date(iso);return Number.isNaN(d.getTime())?null:d;}
  function fmtTime(d){return d?d.toLocaleString("en-GB",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"UTC"})+" UTC":"—";}
  function axisDate(d,span){return span<=2*DAY?d.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",timeZone:"UTC"}):span<=62*DAY?d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",timeZone:"UTC"}):d.toLocaleDateString("en-GB",{month:"short",year:"2-digit",timeZone:"UTC"});}
  function money(v){return Number.isFinite(Number(v))?new Intl.NumberFormat("en",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(v)):"—";}
  function compact(v){return "$"+new Intl.NumberFormat("en",{notation:"compact",maximumFractionDigits:1}).format(Number(v));}
  function pctOr(v){return Number.isFinite(Number(v))?`${Number(v).toFixed(2)}%`:"—";}
  function num(v,d=2,s=""){return Number.isFinite(Number(v))?`${Number(v).toFixed(d)}${s}`:"—";}
  function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
  boot();
})();
