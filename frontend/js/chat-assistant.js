(function(){
  // Keep Bethel's live public trading visibility immediately below the main hero.
  const hero=document.querySelector(".hero");
  const publicBroadcast=document.getElementById("public-broadcast");
  const publicMt5=document.getElementById("public-live-mt5");
  if(hero){
    let priorityAnchor=hero;
    [publicBroadcast,publicMt5].forEach((section)=>{
      if(section){
        priorityAnchor.insertAdjacentElement("afterend",section);
        priorityAnchor=section;
      }
    });
  }

  if(publicMt5){
    const heading=publicMt5.querySelector(".section-header h2");
    if(heading)heading.textContent="LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1";

    if(!document.getElementById("bethel-performance-showcase-style")){
      const style=document.createElement("style");
      style.id="bethel-performance-showcase-style";
      style.textContent=`
        .bethel-performance-showcase{margin:0 0 1.5rem;padding:1.4rem;border:1px solid rgba(16,185,129,.25);border-radius:18px;background:linear-gradient(180deg,rgba(16,185,129,.07),rgba(17,24,39,.88))}
        .bethel-performance-kicker{font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:#10b981;font-weight:700;margin-bottom:.35rem}
        .bethel-performance-title{font-size:1.35rem;font-weight:700;margin-bottom:.35rem}
        .bethel-performance-subtitle{color:var(--text-secondary);font-size:.9rem;margin-bottom:1.2rem}
        .bethel-performance-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:.8rem}
        .bethel-performance-card{padding:1rem;border-radius:13px;border:1px solid var(--border-color);background:rgba(255,255,255,.025)}
        .bethel-performance-card small{display:block;color:var(--text-secondary);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.35rem}
        .bethel-performance-card strong{font-size:1.08rem;word-break:break-word}
        .bethel-performance-card.primary strong{color:#10b981;font-size:1.2rem}
        .bethel-history{margin-top:1.2rem;padding:1rem;border:1px solid var(--border-color);border-radius:14px;background:rgba(0,0,0,.12)}
        .bethel-history-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:.8rem;flex-wrap:wrap}
        .bethel-history-head strong{font-size:.95rem}.bethel-history-legend{font-size:.76rem;color:var(--text-secondary)}
        .bethel-history svg{display:block;width:100%;height:220px;overflow:visible}
        .bethel-history-empty{color:var(--text-secondary);font-size:.9rem;padding:2rem 0;text-align:center}
        .bethel-monthly{margin-top:1.2rem;padding:1rem;border:1px solid var(--border-color);border-radius:14px;background:rgba(0,0,0,.12)}
        .bethel-monthly-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:.85rem;flex-wrap:wrap}
        .bethel-monthly-head strong{font-size:.95rem}.bethel-monthly-head span{font-size:.76rem;color:var(--text-secondary)}
        .bethel-monthly-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:.65rem}
        .bethel-month-card{padding:.8rem;border-radius:11px;border:1px solid var(--border-color);background:rgba(255,255,255,.025);text-align:center}
        .bethel-month-card small{display:block;color:var(--text-secondary);font-size:.72rem;margin-bottom:.25rem}
        .bethel-month-card strong{font-size:1rem}.bethel-month-card.positive strong{color:#10b981}.bethel-month-card.negative strong{color:#f87171}.bethel-month-card.flat strong{color:#d1d5db}
        .bethel-performance-method{margin:.9rem 0 0;color:var(--text-secondary);font-size:.76rem;line-height:1.5}
      `;
      document.head.appendChild(style);
    }

    const shell=publicMt5.querySelector(".live-mt5-shell");
    if(shell&&!document.getElementById("bethel-performance-showcase")){
      const showcase=document.createElement("div");
      showcase.id="bethel-performance-showcase";
      showcase.className="bethel-performance-showcase";
      showcase.innerHTML=`
        <div class="bethel-performance-kicker">Public Performance Record</div>
        <div class="bethel-performance-title">Verified Trading Performance Overview</div>
        <div class="bethel-performance-subtitle">Read-only metrics derived from Bethel's active master-account history.</div>
        <div class="bethel-performance-grid">
          <div class="bethel-performance-card"><small>Account Number</small><strong id="perf-account">—</strong></div>
          <div class="bethel-performance-card"><small>Starting Capital</small><strong id="perf-starting">—</strong></div>
          <div class="bethel-performance-card"><small>Current Balance</small><strong id="perf-balance">—</strong></div>
          <div class="bethel-performance-card"><small>Current Equity</small><strong id="perf-equity">—</strong></div>
          <div class="bethel-performance-card primary"><small>Total Return</small><strong id="perf-return">—</strong></div>
          <div class="bethel-performance-card"><small>Trading Days</small><strong id="perf-days">—</strong></div>
          <div class="bethel-performance-card"><small>Total Trades</small><strong id="perf-trades">—</strong></div>
          <div class="bethel-performance-card"><small>Win Rate</small><strong id="perf-win">—</strong></div>
          <div class="bethel-performance-card"><small>Maximum Drawdown</small><strong id="perf-dd">—</strong></div>
          <div class="bethel-performance-card"><small>Profit Factor</small><strong id="perf-pf">—</strong></div>
        </div>
        <div class="bethel-history">
          <div class="bethel-history-head"><strong>Balance & Equity History</strong><span class="bethel-history-legend">Balance — Equity</span></div>
          <div id="bethel-history-chart" class="bethel-history-empty">Loading recorded performance history…</div>
        </div>
        <div class="bethel-monthly">
          <div class="bethel-monthly-head"><strong>Monthly Returns</strong><span>Recorded equity return by month</span></div>
          <div id="bethel-monthly-grid" class="bethel-monthly-grid"><div class="bethel-history-empty">Loading monthly returns…</div></div>
        </div>
        <p id="bethel-performance-method" class="bethel-performance-method">Performance information is read-only. Past performance does not guarantee future results.</p>
      `;
      const liveHeading=shell.querySelector(".live-mt5-heading");
      if(liveHeading)liveHeading.insertAdjacentElement("afterend",showcase);else shell.prepend(showcase);
    }

    const perfSet=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value==null?"—":String(value)};
    const perfMoney=(value,currency)=>{
      if(value==null)return "—";
      try{return new Intl.NumberFormat(undefined,{style:"currency",currency:currency||"USD",maximumFractionDigits:2}).format(Number(value))}
      catch(_){return Number(value).toFixed(2)+" "+(currency||"USD")}
    };
    const pct=(value)=>value==null?"—":`${Number(value).toFixed(2)}%`;

    function drawHistory(points){
      const target=document.getElementById("bethel-history-chart");if(!target)return;
      const clean=(points||[]).filter(p=>Number.isFinite(Number(p.balance))&&Number.isFinite(Number(p.equity)));
      if(clean.length<2){target.className="bethel-history-empty";target.textContent="Historical chart will appear as recorded performance data accumulates.";return}
      const W=900,H=220,pad=18;
      const values=clean.flatMap(p=>[Number(p.balance),Number(p.equity)]);
      let min=Math.min(...values),max=Math.max(...values);if(max===min){max+=1;min-=1}
      const x=i=>pad+(i/(clean.length-1))*(W-pad*2);
      const y=v=>H-pad-((v-min)/(max-min))*(H-pad*2);
      const balance=clean.map((p,i)=>`${x(i).toFixed(1)},${y(Number(p.balance)).toFixed(1)}`).join(" ");
      const equity=clean.map((p,i)=>`${x(i).toFixed(1)},${y(Number(p.equity)).toFixed(1)}`).join(" ");
      target.className="";
      target.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Balance and equity history"><line x1="${pad}" y1="${H-pad}" x2="${W-pad}" y2="${H-pad}" stroke="rgba(156,163,175,.25)"/><polyline points="${balance}" fill="none" stroke="#10b981" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/><polyline points="${equity}" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/></svg>`;
    }

    function renderMonthlyReturns(points){
      const target=document.getElementById("bethel-monthly-grid");if(!target)return;
      const clean=(points||[]).filter(p=>p.timestamp&&Number.isFinite(Number(p.equity))).sort((a,b)=>new Date(a.timestamp)-new Date(b.timestamp));
      if(clean.length<2){target.innerHTML='<div class="bethel-history-empty">Monthly returns will appear as recorded performance history accumulates.</div>';return}
      const months=new Map();
      clean.forEach(p=>{
        const d=new Date(p.timestamp);if(Number.isNaN(d.getTime()))return;
        const key=`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,"0")}`;
        const existing=months.get(key);const equity=Number(p.equity);
        if(!existing)months.set(key,{first:equity,last:equity});else existing.last=equity;
      });
      const rows=[...months.entries()].map(([month,v])=>({month,returnPercent:v.first?((v.last-v.first)/v.first)*100:null})).filter(r=>r.returnPercent!=null);
      if(!rows.length){target.innerHTML='<div class="bethel-history-empty">Monthly returns are not yet available.</div>';return}
      target.innerHTML=rows.map(r=>{
        const [year,month]=r.month.split("-");
        const label=new Date(Date.UTC(Number(year),Number(month)-1,1)).toLocaleDateString(undefined,{month:"short",year:"numeric",timeZone:"UTC"});
        const n=Number(r.returnPercent);const cls=n>0?"positive":n<0?"negative":"flat";const sign=n>0?"+":"";
        return `<div class="bethel-month-card ${cls}"><small>${label}</small><strong>${sign}${n.toFixed(2)}%</strong></div>`;
      }).join("");
    }

    const loadPerformanceContext=async()=>{
      try{
        const [summaryResponse,historyResponse]=await Promise.all([
          fetch("https://api.betheltradingtechnologies.com/performance/public-summary?ts="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"}}),
          fetch("https://api.betheltradingtechnologies.com/performance/public-history?ts="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"}})
        ]);
        if(summaryResponse.ok){
          const d=await summaryResponse.json();
          if(d.available){
            perfSet("perf-account",d.account_number||"—");
            perfSet("perf-starting",perfMoney(d.starting_balance,d.currency));
            perfSet("perf-balance",perfMoney(d.current_balance,d.currency));
            perfSet("perf-equity",perfMoney(d.current_equity,d.currency));
            perfSet("perf-return",pct(d.total_return_percent));
            perfSet("perf-days",d.trading_days||0);
            perfSet("perf-trades",d.total_trades||0);
            perfSet("perf-win",pct(d.win_rate));
            perfSet("perf-dd",pct(d.maximum_drawdown_percent));
            perfSet("perf-pf",d.profit_factor==null?"—":Number(d.profit_factor).toFixed(2));
            const method=document.getElementById("bethel-performance-method");if(method&&d.methodology)method.textContent=d.methodology+" Past performance does not guarantee future results.";
          }
        }
        if(historyResponse.ok){const h=await historyResponse.json();if(h.available){drawHistory(h.points);renderMonthlyReturns(h.points)}}
      }catch(_){}
    };
    loadPerformanceContext();window.setInterval(loadPerformanceContext,60000);
  }

  const API="https://api.betheltradingtechnologies.com/public/assistant/chat";
  const SUPPORT="info@betheltradingtechnologies.com";
  const launcher=document.createElement("button");
  launcher.className="bethel-chat-launcher";
  launcher.type="button";
  launcher.setAttribute("aria-label","Open Bethel website assistant");
  launcher.innerHTML='<i class="fa-solid fa-comments" aria-hidden="true"></i><span>Ask Bethel</span>';

  const panel=document.createElement("section");
  panel.className="bethel-chat-panel";
  panel.setAttribute("aria-label","Bethel website assistant");
  panel.innerHTML=`
    <div class="bethel-chat-header">
      <div><div class="bethel-chat-title">Bethel Assistant</div><div class="bethel-chat-subtitle">Quick general questions</div></div>
      <button class="bethel-chat-close" type="button" aria-label="Close assistant">&times;</button>
    </div>
    <div class="bethel-chat-messages" aria-live="polite"></div>
    <form class="bethel-chat-form">
      <input class="bethel-chat-input" maxlength="500" autocomplete="off" placeholder="Ask a question…" aria-label="Your question">
      <button class="bethel-chat-send" type="submit">Send</button>
    </form>
    <div class="bethel-chat-note">For all inquiries, email <a href="mailto:${SUPPORT}">${SUPPORT}</a>. General information only.</div>`;

  document.body.appendChild(panel);
  document.body.appendChild(launcher);

  const messages=panel.querySelector(".bethel-chat-messages");
  const form=panel.querySelector(".bethel-chat-form");
  const input=panel.querySelector(".bethel-chat-input");
  const send=panel.querySelector(".bethel-chat-send");

  function ensureSupportEmail(text){
    const value=String(text||"").trim();
    if(value.toLowerCase().includes(SUPPORT.toLowerCase()))return value;
    return (value?value+"\n\n":"")+"For further inquiries, email: "+SUPPORT;
  }

  function addMessage(text,who){
    const item=document.createElement("div");
    item.className="bethel-chat-message "+who;
    const parts=String(text).split(SUPPORT);
    parts.forEach((part,index)=>{
      item.appendChild(document.createTextNode(part));
      if(index<parts.length-1){const a=document.createElement("a");a.href="mailto:"+SUPPORT;a.textContent=SUPPORT;item.appendChild(a);}
    });
    messages.appendChild(item);
    messages.scrollTop=messages.scrollHeight;
  }

  addMessage(ensureSupportEmail("Hello! I’m the Bethel website assistant. Ask me a quick question about Bethel, registration, services or general support."),"bot");

  launcher.addEventListener("click",()=>{panel.classList.toggle("open");if(panel.classList.contains("open"))input.focus();});
  panel.querySelector(".bethel-chat-close").addEventListener("click",()=>panel.classList.remove("open"));

  form.addEventListener("submit",async(event)=>{
    event.preventDefault();
    const question=input.value.trim();
    if(!question)return;
    addMessage(question,"user");
    input.value=""; input.disabled=true; send.disabled=true;
    try{
      const response=await fetch(API,{method:"POST",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({message:question})});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||"Assistant unavailable");
      addMessage(ensureSupportEmail(data.answer||"I can’t confirm that right now."),"bot");
    }catch(_){
      addMessage(ensureSupportEmail("I’m unable to answer that right now. The Bethel team can help you."),"bot");
    }finally{
      input.disabled=false;send.disabled=false;input.focus();
    }
  });

  if(!document.querySelector('link[href*="visitor-reviews.css"]')){const l=document.createElement("link");l.rel="stylesheet";l.href="css/visitor-reviews.css?v=1";document.head.appendChild(l);}
  if(!document.querySelector('script[src*="visitor-reviews.js"]')){const s=document.createElement("script");s.src="js/visitor-reviews.js?v=1";s.defer=true;document.body.appendChild(s);}
})();