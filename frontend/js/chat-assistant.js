(function(){
  const API_BASE="https://api.betheltradingtechnologies.com";
  const SUPPORT="info@betheltradingtechnologies.com";
  const hero=document.querySelector(".hero");
  const publicBroadcast=document.getElementById("public-broadcast");
  const publicMt5=document.getElementById("public-live-mt5");

  // Funding-readiness corrections: remove unsupported independent-verification claims.
  const performance=document.getElementById("performance");
  if(performance){
    const heading=performance.querySelector(".section-header h2");
    const intro=performance.querySelector(".section-header p");
    const box=performance.querySelector(".performance-box");
    const links=performance.querySelector(".platforms-container");
    if(heading)heading.textContent="Trading Performance";
    if(intro)intro.textContent="Bethel-reported performance and live read-only telemetry from the selected master terminal.";
    if(box){
      const p=box.querySelector("p");
      if(p)p.textContent="Performance displayed on this website is reported by Bethel from its own systems and should not be interpreted as independent third-party verification.";
    }
    if(links)links.remove();
  }

  // Replace open registration with invitation/pre-launch access requests.
  document.querySelectorAll('a[href*="investor-frontend/onboarding.html"]').forEach((link)=>{
    link.href=`mailto:${SUPPORT}?subject=${encodeURIComponent("Bethel pre-launch access request")}`;
    if(link.classList.contains("nav-onboarding"))link.textContent="Request Access";
    else if(link.classList.contains("onboarding-float"))link.textContent="Request Pre-Launch Access →";
    else link.textContent="Request Access";
  });
  document.querySelectorAll(".hero .btn").forEach((link)=>{
    if((link.textContent||"").toLowerCase().includes("verified performance"))link.textContent="View Live Performance";
  });

  // Add a visible pre-launch / diligence notice.
  if(hero&&!document.getElementById("bethel-prelaunch-notice")){
    const notice=document.createElement("div");
    notice.id="bethel-prelaunch-notice";
    notice.style.cssText="max-width:900px;margin:-3.5rem auto 2rem;padding:1rem 1.25rem;border:1px solid rgba(245,158,11,.38);border-radius:14px;background:rgba(245,158,11,.08);color:#d1d5db;font-size:.88rem;line-height:1.6;text-align:center";
    notice.innerHTML='<strong style="color:#fbbf24">PRE-LAUNCH NOTICE:</strong> Bethel is completing corporate, contractual and regulatory work with professional advisers. Public account access is invitation-only. Live trading information shown below is Bethel-reported read-only telemetry and is not represented as independent third-party verification.';
    hero.insertAdjacentElement("afterend",notice);
  }

  // Prioritize live public trading visibility immediately below the company hero/notice.
  const priorityStart=document.getElementById("bethel-prelaunch-notice")||hero;
  if(priorityStart){
    let anchor=priorityStart;
    [publicBroadcast,publicMt5].forEach((section)=>{
      if(section){anchor.insertAdjacentElement("afterend",section);anchor=section;}
    });
  }

  if(publicBroadcast){
    const status=publicBroadcast.querySelector(".public-broadcast-status");
    const note=publicBroadcast.querySelector(".public-broadcast-note");
    if(status)status.textContent="BETHEL LIVE READ-ONLY SESSION";
    if(note)note.textContent="BETHEL-REPORTED READ-ONLY TELEMETRY · Not independent third-party verification. MetaTrader EA remains the execution owner. Past performance does not guarantee future results.";
  }

  if(publicMt5){
    const heading=publicMt5.querySelector(".section-header h2");
    const sub=publicMt5.querySelector(".section-header p");
    if(heading)heading.textContent="LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1";
    if(sub)sub.textContent="Bethel-reported read-only account telemetry from the selected authorized master terminal.";

    if(!document.getElementById("bethel-performance-showcase-style")){
      const style=document.createElement("style");
      style.id="bethel-performance-showcase-style";
      style.textContent=`
        .bethel-performance-showcase{margin:0 0 1.5rem;padding:1.4rem;border:1px solid rgba(16,185,129,.25);border-radius:18px;background:linear-gradient(180deg,rgba(16,185,129,.07),rgba(17,24,39,.88))}
        .bethel-performance-kicker{font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:#10b981;font-weight:700;margin-bottom:.35rem}
        .bethel-performance-title{font-size:1.35rem;font-weight:700;margin-bottom:.35rem}.bethel-performance-subtitle{color:var(--text-secondary);font-size:.9rem;margin-bottom:1.2rem}
        .bethel-performance-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:.8rem}.bethel-performance-card{padding:1rem;border-radius:13px;border:1px solid var(--border-color);background:rgba(255,255,255,.025)}
        .bethel-performance-card small{display:block;color:var(--text-secondary);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.35rem}.bethel-performance-card strong{font-size:1.08rem;word-break:break-word}.bethel-performance-card.primary strong{color:#10b981;font-size:1.2rem}
        .bethel-history,.bethel-monthly{margin-top:1.2rem;padding:1rem;border:1px solid var(--border-color);border-radius:14px;background:rgba(0,0,0,.12)}.bethel-history-head,.bethel-monthly-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:.85rem;flex-wrap:wrap}
        .bethel-history-head strong,.bethel-monthly-head strong{font-size:.95rem}.bethel-history-legend,.bethel-monthly-head span{font-size:.76rem;color:var(--text-secondary)}.bethel-history svg{display:block;width:100%;height:220px;overflow:visible}.bethel-history-empty{color:var(--text-secondary);font-size:.9rem;padding:2rem 0;text-align:center}
        .bethel-monthly-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:.65rem}.bethel-month-card{padding:.8rem;border-radius:11px;border:1px solid var(--border-color);background:rgba(255,255,255,.025);text-align:center}.bethel-month-card small{display:block;color:var(--text-secondary);font-size:.72rem;margin-bottom:.25rem}.bethel-month-card strong{font-size:1rem}.bethel-month-card.positive strong{color:#10b981}.bethel-month-card.negative strong{color:#f87171}.bethel-month-card.flat strong{color:#d1d5db}
        .bethel-performance-method{margin:.9rem 0 0;color:var(--text-secondary);font-size:.76rem;line-height:1.5}.bethel-diligence{max-width:1200px;margin:0 auto 3rem;padding:1.5rem 2rem}.bethel-diligence-card{border:1px solid var(--border-color);border-radius:16px;background:var(--card-bg);padding:1.4rem}.bethel-diligence h3{margin-bottom:.7rem}.bethel-diligence p{color:var(--text-secondary);font-size:.88rem;line-height:1.6;margin:.45rem 0}.bethel-diligence a{color:#10b981}
      `;
      document.head.appendChild(style);
    }

    const shell=publicMt5.querySelector(".live-mt5-shell");
    if(shell&&!document.getElementById("bethel-performance-showcase")){
      const showcase=document.createElement("div");
      showcase.id="bethel-performance-showcase";showcase.className="bethel-performance-showcase";
      showcase.innerHTML=`
        <div class="bethel-performance-kicker">Bethel-Reported Performance Record</div>
        <div class="bethel-performance-title">Live Trading Performance Overview</div>
        <div class="bethel-performance-subtitle">Read-only metrics derived from Bethel's selected active master-account history. This is not an independent third-party verification service.</div>
        <div class="bethel-performance-grid">
          <div class="bethel-performance-card"><small>Account Number</small><strong id="perf-account">—</strong></div><div class="bethel-performance-card"><small>Starting Capital</small><strong id="perf-starting">—</strong></div><div class="bethel-performance-card"><small>Current Balance</small><strong id="perf-balance">—</strong></div><div class="bethel-performance-card"><small>Current Equity</small><strong id="perf-equity">—</strong></div><div class="bethel-performance-card primary"><small>Total Return</small><strong id="perf-return">—</strong></div><div class="bethel-performance-card"><small>Trading Days</small><strong id="perf-days">—</strong></div><div class="bethel-performance-card"><small>Total Trades</small><strong id="perf-trades">—</strong></div><div class="bethel-performance-card"><small>Win Rate</small><strong id="perf-win">—</strong></div><div class="bethel-performance-card"><small>Maximum Drawdown</small><strong id="perf-dd">—</strong></div><div class="bethel-performance-card"><small>Profit Factor</small><strong id="perf-pf">—</strong></div>
        </div>
        <div class="bethel-history"><div class="bethel-history-head"><strong>Balance & Equity History</strong><span class="bethel-history-legend">Balance — Equity</span></div><div id="bethel-history-chart" class="bethel-history-empty">Loading recorded performance history…</div></div>
        <div class="bethel-monthly"><div class="bethel-monthly-head"><strong>Monthly Returns</strong><span>Bethel-recorded equity return by month</span></div><div id="bethel-monthly-grid" class="bethel-monthly-grid"><div class="bethel-history-empty">Loading monthly returns…</div></div></div>
        <p id="bethel-performance-method" class="bethel-performance-method">Bethel-reported read-only performance data. Not independently verified. Past performance does not guarantee future results.</p>`;
      const liveHeading=shell.querySelector(".live-mt5-heading");if(liveHeading)liveHeading.insertAdjacentElement("afterend",showcase);else shell.prepend(showcase);
    }

    const set=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value==null?"—":String(value)};
    const money=(value,currency)=>{if(value==null)return "—";try{return new Intl.NumberFormat(undefined,{style:"currency",currency:currency||"USD",maximumFractionDigits:2}).format(Number(value))}catch(_){return Number(value).toFixed(2)+" "+(currency||"USD")}};
    const pct=(value)=>value==null?"—":`${Number(value).toFixed(2)}%`;
    function drawHistory(points){const target=document.getElementById("bethel-history-chart");if(!target)return;const clean=(points||[]).filter(p=>Number.isFinite(Number(p.balance))&&Number.isFinite(Number(p.equity)));if(clean.length<2){target.className="bethel-history-empty";target.textContent="Historical chart will appear as recorded performance data accumulates.";return}const W=900,H=220,pad=18,values=clean.flatMap(p=>[Number(p.balance),Number(p.equity)]);let min=Math.min(...values),max=Math.max(...values);if(max===min){max+=1;min-=1}const x=i=>pad+(i/(clean.length-1))*(W-pad*2),y=v=>H-pad-((v-min)/(max-min))*(H-pad*2),balance=clean.map((p,i)=>`${x(i).toFixed(1)},${y(Number(p.balance)).toFixed(1)}`).join(" "),equity=clean.map((p,i)=>`${x(i).toFixed(1)},${y(Number(p.equity)).toFixed(1)}`).join(" ");target.className="";target.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Balance and equity history"><line x1="${pad}" y1="${H-pad}" x2="${W-pad}" y2="${H-pad}" stroke="rgba(156,163,175,.25)"/><polyline points="${balance}" fill="none" stroke="#10b981" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/><polyline points="${equity}" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/></svg>`;}
    function renderMonthly(points){const target=document.getElementById("bethel-monthly-grid");if(!target)return;const clean=(points||[]).filter(p=>p.timestamp&&Number.isFinite(Number(p.equity))).sort((a,b)=>new Date(a.timestamp)-new Date(b.timestamp));if(clean.length<2){target.innerHTML='<div class="bethel-history-empty">Monthly returns will appear as recorded history accumulates.</div>';return}const months=new Map();clean.forEach(p=>{const d=new Date(p.timestamp);if(Number.isNaN(d.getTime()))return;const key=`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,"0")}`,e=Number(p.equity),old=months.get(key);if(!old)months.set(key,{first:e,last:e});else old.last=e;});const rows=[...months.entries()].map(([month,v])=>({month,r:v.first?((v.last-v.first)/v.first)*100:null})).filter(x=>x.r!=null);target.innerHTML=rows.map(x=>{const [yr,mo]=x.month.split("-"),label=new Date(Date.UTC(Number(yr),Number(mo)-1,1)).toLocaleDateString(undefined,{month:"short",year:"numeric",timeZone:"UTC"}),n=Number(x.r),cls=n>0?"positive":n<0?"negative":"flat",sign=n>0?"+":"";return `<div class="bethel-month-card ${cls}"><small>${label}</small><strong>${sign}${n.toFixed(2)}%</strong></div>`;}).join("")||'<div class="bethel-history-empty">Monthly returns are not yet available.</div>';}
    async function loadPerformance(){try{const [sr,hr]=await Promise.all([fetch(API_BASE+"/performance/public-summary?ts="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"}}),fetch(API_BASE+"/performance/public-history?ts="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"}})]);if(sr.ok){const d=await sr.json();if(d.available){set("perf-account",d.account_number||"—");set("perf-starting",money(d.starting_balance,d.currency));set("perf-balance",money(d.current_balance,d.currency));set("perf-equity",money(d.current_equity,d.currency));set("perf-return",pct(d.total_return_percent));set("perf-days",d.trading_days||0);set("perf-trades",d.total_trades||0);set("perf-win",pct(d.win_rate));set("perf-dd",pct(d.maximum_drawdown_percent));set("perf-pf",d.profit_factor==null?"—":Number(d.profit_factor).toFixed(2));}}if(hr.ok){const h=await hr.json();if(h.available){drawHistory(h.points);renderMonthly(h.points);}}}catch(_){} }
    loadPerformance();window.setInterval(loadPerformance,60000);
  }

  // Interim privacy, complaints and corporate-status disclosure for funding diligence.
  const footer=document.querySelector("footer");
  if(footer&&!document.getElementById("bethel-diligence-disclosure")){
    const block=document.createElement("section");block.id="bethel-diligence-disclosure";block.className="bethel-diligence";
    block.innerHTML=`<div class="bethel-diligence-card"><h3>Pre-Launch, Privacy & Contact Information</h3><p><strong>Status:</strong> Bethel is in a pre-launch/funding-readiness phase. Corporate and regulatory particulars are being finalized with qualified advisers and will be published once confirmed. Public onboarding is invitation-only.</p><p><strong>Interim privacy notice:</strong> Information submitted through contact, account, identity or support channels may be used to provide and secure the platform, respond to inquiries, prevent fraud, maintain audit records and meet applicable legal or contractual obligations. Information may be processed by contracted infrastructure, identity, compliance and professional-service providers where necessary. Bethel does not sell personal information.</p><p><strong>Privacy requests & complaints:</strong> Email <a href="mailto:${SUPPORT}">${SUPPORT}</a>. Do not send passwords, one-time codes, private keys, API secrets, PINs or full card details by email.</p><p><strong>Performance disclosure:</strong> Website performance and MT5 telemetry are Bethel-reported from the selected master terminal and are not represented as independent third-party verification. Past performance does not guarantee future results.</p></div>`;
    footer.insertAdjacentElement("beforebegin",block);
  }

  // Website assistant.
  const API=API_BASE+"/public/assistant/chat";
  const launcher=document.createElement("button");launcher.className="bethel-chat-launcher";launcher.type="button";launcher.setAttribute("aria-label","Open Bethel website assistant");launcher.innerHTML='<i class="fa-solid fa-comments" aria-hidden="true"></i><span>Ask Bethel</span>';
  const panel=document.createElement("section");panel.className="bethel-chat-panel";panel.setAttribute("aria-label","Bethel website assistant");panel.innerHTML=`<div class="bethel-chat-header"><div><div class="bethel-chat-title">Bethel Assistant</div><div class="bethel-chat-subtitle">Quick general questions</div></div><button class="bethel-chat-close" type="button" aria-label="Close assistant">&times;</button></div><div class="bethel-chat-messages" aria-live="polite"></div><form class="bethel-chat-form"><input class="bethel-chat-input" maxlength="500" autocomplete="off" placeholder="Ask a question…" aria-label="Your question"><button class="bethel-chat-send" type="submit">Send</button></form><div class="bethel-chat-note">For inquiries, privacy requests or complaints, email <a href="mailto:${SUPPORT}">${SUPPORT}</a>. General information only.</div>`;
  document.body.appendChild(panel);document.body.appendChild(launcher);
  const messages=panel.querySelector(".bethel-chat-messages"),form=panel.querySelector(".bethel-chat-form"),input=panel.querySelector(".bethel-chat-input"),send=panel.querySelector(".bethel-chat-send");
  const supportText=(text)=>{const v=String(text||"").trim();return v.toLowerCase().includes(SUPPORT.toLowerCase())?v:(v?v+"\n\n":"")+"For further inquiries: "+SUPPORT;};
  function addMessage(text,who){const item=document.createElement("div");item.className="bethel-chat-message "+who;const parts=String(text).split(SUPPORT);parts.forEach((part,index)=>{item.appendChild(document.createTextNode(part));if(index<parts.length-1){const a=document.createElement("a");a.href="mailto:"+SUPPORT;a.textContent=SUPPORT;item.appendChild(a);}});messages.appendChild(item);messages.scrollTop=messages.scrollHeight;}
  addMessage(supportText("Hello! I’m the Bethel website assistant. Bethel is currently operating on a pre-launch, invitation-only basis. Ask a general question about the company, technology or support."),"bot");
  launcher.addEventListener("click",()=>{panel.classList.toggle("open");if(panel.classList.contains("open"))input.focus();});panel.querySelector(".bethel-chat-close").addEventListener("click",()=>panel.classList.remove("open"));
  form.addEventListener("submit",async(event)=>{event.preventDefault();const question=input.value.trim();if(!question)return;addMessage(question,"user");input.value="";input.disabled=true;send.disabled=true;try{const response=await fetch(API,{method:"POST",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({message:question})});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error();addMessage(supportText(data.answer||"I can’t confirm that right now."),"bot");}catch(_){addMessage(supportText("I’m unable to answer that right now. The Bethel team can help you."),"bot");}finally{input.disabled=false;send.disabled=false;input.focus();}});

  if(!document.querySelector('link[href*="visitor-reviews.css"]')){const l=document.createElement("link");l.rel="stylesheet";l.href="css/visitor-reviews.css?v=1";document.head.appendChild(l);}
  if(!document.querySelector('script[src*="visitor-reviews.js"]')){const s=document.createElement("script");s.src="js/visitor-reviews.js?v=1";s.defer=true;document.body.appendChild(s);}
})();