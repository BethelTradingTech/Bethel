/*
Bethel Trading Technologies
Super Admin Account Growth Chart

Admin-only extension. Uses protected performance/equity APIs and never modifies
investor/subscriber-facing pages or trading execution.
*/
(function(){
    "use strict";

    let initialized=false;

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
        if(initialized)return;initialized=true;
        injectStyles();buildPanel();
        document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(loadGrowth,80));
        document.querySelector("#refresh-button")?.addEventListener("click",()=>{
            if(document.querySelector("#view-analytics")?.classList.contains("active"))setTimeout(loadGrowth,120);
        });
        window.addEventListener("resize",()=>{
            if(document.querySelector("#view-analytics")?.classList.contains("active"))setTimeout(loadGrowth,80);
        });
        if(document.querySelector("#view-analytics")?.classList.contains("active"))loadGrowth();
    }

    function injectStyles(){
        if(document.querySelector("#bethel-performance-growth-style"))return;
        const style=document.createElement("style");style.id="bethel-performance-growth-style";
        style.textContent=`
          .bethel-growth-panel{margin-top:18px}
          .bethel-growth-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
          .bethel-growth-card{padding:13px 14px;border-radius:12px;background:rgba(8,18,33,.68);border:1px solid rgba(148,163,184,.16)}
          .bethel-growth-card small{display:block;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;font-size:.72rem}
          .bethel-growth-card strong{font-size:1.25rem}
          .bethel-growth-chart-wrap{position:relative;width:100%;overflow:hidden;border-radius:12px;background:rgba(2,6,23,.45)}
          #bethel-growth-chart{display:block;width:100%;height:360px}
          .bethel-growth-legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;color:#cbd5e1;font-size:.8rem}
          .bethel-growth-legend span:before{content:"";display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor}
          .bethel-growth-note{color:#94a3b8;font-size:.8rem;margin-top:10px}
          @media(max-width:900px){#bethel-growth-chart{height:290px}}
        `;document.head.appendChild(style);
    }

    function buildPanel(){
        const view=document.querySelector("#view-analytics");
        if(!view||document.querySelector("#bethel-performance-growth"))return;
        const panel=document.createElement("article");panel.id="bethel-performance-growth";panel.className="panel bethel-growth-panel";
        panel.innerHTML=`
          <div class="section-heading"><div><h2>Account Growth & Performance</h2><p>Balance and equity growth across the active master account's full performance-history window.</p></div><button id="bethel-growth-reload" type="button">Refresh chart</button></div>
          <div id="bethel-growth-summary" class="bethel-growth-summary"></div>
          <div class="bethel-growth-chart-wrap"><canvas id="bethel-growth-chart"></canvas></div>
          <div class="bethel-growth-legend"><span>Equity</span><span>Balance</span></div>
          <p class="bethel-growth-note">The graph uses the same account-history window as Bethel performance analytics. It plots all available signed MT5 equity and balance snapshots for the active master account in that period. Deposits and withdrawals can change raw account values; headline Total Return remains cash-flow adjusted.</p>
        `;
        const risk=document.querySelector("#bethel-risk-monitor");if(risk)view.insertBefore(panel,risk);else view.appendChild(panel);
        document.querySelector("#bethel-growth-reload")?.addEventListener("click",loadGrowth);
    }

    async function loadGrowth(){
        buildPanel();const button=document.querySelector("#bethel-growth-reload");
        if(button){button.disabled=true;button.textContent="Refreshing…";}
        try{
            const [analytics,historyResponse]=await Promise.all([
                window.apiGet("/performance/analytics"),
                window.apiGet("/performance/equity-history")
            ]);
            const account=String(analytics?.master_account||"").trim();
            const historyDays=Number(analytics?.history_days);
            let allRows=(historyResponse?.history||[])
                .filter(row=>!account||String(row.account_number||"").trim()===account)
                .filter(row=>Number.isFinite(Number(row.equity))&&Number(row.equity)>0&&row.timestamp)
                .sort((a,b)=>new Date(normalizeTimestamp(a.timestamp))-new Date(normalizeTimestamp(b.timestamp)));

            let rows=allRows;
            let windowStart=null;
            let windowEnd=allRows.length?parseDate(allRows[allRows.length-1].timestamp):null;
            if(windowEnd&&Number.isFinite(historyDays)&&historyDays>0){
                windowStart=new Date(windowEnd.getTime()-(historyDays*86400000));
                rows=allRows.filter(row=>{
                    const at=parseDate(row.timestamp);
                    return at&&at>=windowStart&&at<=windowEnd;
                });
            }

            renderSummary(rows,analytics,account,historyDays,windowStart,windowEnd);
            drawChart(dailySeries(rows));
        }catch(error){
            const target=document.querySelector("#bethel-growth-summary");
            if(target)target.innerHTML=`<div class="bethel-growth-card"><small>Chart status</small><strong>Unavailable</strong><div>${escapeText(error?.message||"Unable to load account history")}</div></div>`;
            drawChart([]);
        }finally{if(button){button.disabled=false;button.textContent="Refresh chart";}}
    }

    function normalizeTimestamp(value){
        const text=String(value||"").trim();
        if(!text)return text;
        if(/[zZ]$|[+-]\d\d:?\d\d$/.test(text))return text;
        return text.replace(" ","T")+"Z";
    }

    function parseDate(value){
        if(!value)return null;const d=new Date(normalizeTimestamp(value));return Number.isNaN(d.getTime())?null:d;
    }

    function dailySeries(rows){
        const map=new Map();
        rows.forEach(row=>{const date=String(row.timestamp).slice(0,10);map.set(date,{date,equity:Number(row.equity),balance:Number(row.balance||0)});});
        return [...map.values()].sort((a,b)=>a.date.localeCompare(b.date));
    }

    function renderSummary(rows,analytics,account,historyDays,windowStart,windowEnd){
        const target=document.querySelector("#bethel-growth-summary");if(!target)return;
        if(!rows.length){
            target.innerHTML=[
                card("Master account",account||"—"),
                card("Account history",Number.isFinite(historyDays)?`${historyDays.toFixed(1)} days`:"—"),
                card("History","No snapshots in analytics window")
            ].join("");return;
        }
        const first=rows[0],last=rows[rows.length-1];
        const startEq=Number(first.equity||0),currentEq=Number(last.equity||0);
        const rawGrowth=startEq>0?((currentEq/startEq)-1)*100:null;
        const startLabel=windowStart?formatDate(windowStart):String(first.timestamp).slice(0,10);
        const endLabel=windowEnd?formatDate(windowEnd):String(last.timestamp).slice(0,10);
        target.innerHTML=[
            card("Master account",account||"—"),
            card("Account history",Number.isFinite(historyDays)?`${historyDays.toFixed(1)} days`:"—"),
            card("History start",startLabel),
            card("History end",endLabel),
            card("Starting equity",money(startEq)),
            card("Current equity",money(currentEq)),
            card("Raw equity growth",rawGrowth===null?"—":pct(rawGrowth)),
            card("Total return",Number.isFinite(Number(analytics?.total_return_percent))?pct(Number(analytics.total_return_percent)):"—"),
            card("Snapshots plotted",String(rows.length))
        ].join("");
    }

    function card(label,value){return `<div class="bethel-growth-card"><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong></div>`;}

    function drawChart(series){
        const canvas=document.querySelector("#bethel-growth-chart");if(!canvas)return;
        const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
        const width=Math.max(520,Math.floor(rect.width||900)),height=Math.max(260,Math.floor(rect.height||360));
        canvas.width=width*dpr;canvas.height=height*dpr;
        const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);ctx.font="12px system-ui";ctx.fillStyle="#94a3b8";
        if(!series.length){ctx.fillText("No account-history snapshots available for this period.",24,40);return;}
        const pad={l:72,r:24,t:24,b:42},plotW=width-pad.l-pad.r,plotH=height-pad.t-pad.b;
        const values=series.flatMap(p=>[p.equity,p.balance]).filter(Number.isFinite);
        let min=Math.min(...values),max=Math.max(...values);if(max===min){max+=1;min-=1;}const spread=max-min;min-=spread*.05;max+=spread*.08;
        const times=series.map(p=>Date.parse(p.date+"T00:00:00Z"));
        const minTime=Math.min(...times),maxTime=Math.max(...times);
        const x=i=>pad.l+(maxTime===minTime?plotW/2:((times[i]-minTime)/(maxTime-minTime))*plotW),y=v=>pad.t+((max-v)/(max-min))*plotH;
        ctx.strokeStyle="rgba(148,163,184,.18)";ctx.lineWidth=1;
        for(let i=0;i<=4;i++){
            const yy=pad.t+(plotH*i/4);ctx.beginPath();ctx.moveTo(pad.l,yy);ctx.lineTo(width-pad.r,yy);ctx.stroke();
            const val=max-((max-min)*i/4);ctx.fillStyle="#94a3b8";ctx.fillText(compactMoney(val),8,yy+4);
        }
        drawLine(ctx,series,p=>p.equity,x,y,"#22d3ee",2.6);drawLine(ctx,series,p=>p.balance,x,y,"#a78bfa",2.1);
        const ticks=Math.min(5,series.length);
        for(let i=0;i<ticks;i++){
            const targetTime=minTime+((maxTime-minTime)*(i/(Math.max(1,ticks-1))));
            let index=0,best=Infinity;
            times.forEach((time,j)=>{const distance=Math.abs(time-targetTime);if(distance<best){best=distance;index=j;}});
            const label=series[index].date.slice(5);
            ctx.fillStyle="#94a3b8";ctx.fillText(label,Math.max(pad.l-8,x(index)-18),height-15);
        }
    }

    function drawLine(ctx,series,getValue,x,y,color,width){
        ctx.beginPath();let started=false;
        series.forEach((p,i)=>{const v=Number(getValue(p));if(!Number.isFinite(v))return;const xx=x(i),yy=y(v);if(!started){ctx.moveTo(xx,yy);started=true;}else ctx.lineTo(xx,yy);});
        ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();
    }

    function formatDate(d){return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});}
    function money(v){try{return new Intl.NumberFormat("en",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(v));}catch{return Number(v).toFixed(2);}}
    function compactMoney(v){return "$"+new Intl.NumberFormat("en",{notation:"compact",maximumFractionDigits:1}).format(Number(v));}
    function pct(v){return `${Number(v).toFixed(2)}%`;}
    function escapeText(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

    waitForRuntime();
})();
