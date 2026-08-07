/*
Bethel Trading Technologies
Super Admin Performance Growth Chart

Admin-only, read-only visualization. The chart uses the active master account's
protected MT5 equity snapshots plus recorded external cash flows. It never
modifies investor/subscriber pages or trading execution.
*/
(function(){
    "use strict";

    const DAY_MS=86400000;
    const RANGE_MS={"1D":DAY_MS,"1W":7*DAY_MS,"1M":31*DAY_MS,"3M":93*DAY_MS,"6M":186*DAY_MS,"1Y":366*DAY_MS};
    const state={initialized:false,mode:"return",range:"TOTAL",analytics:null,rows:[],cashFlows:[],series:[],visible:[],geometry:null};

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
        injectStyles();
        buildPanel();
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
          .bethel-growth-panel{margin-top:18px}
          .bethel-growth-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}
          .bethel-growth-head h2{margin-bottom:5px}.bethel-growth-head p{margin:0;color:#94a3b8}
          .bethel-growth-tools{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
          .bethel-growth-tabs,.bethel-growth-ranges{display:flex;gap:4px;padding:4px;border-radius:10px;background:rgba(2,6,23,.52);border:1px solid rgba(148,163,184,.14)}
          .bethel-growth-tabs button,.bethel-growth-ranges button{border:0;background:transparent;color:#94a3b8;padding:7px 10px;border-radius:7px;cursor:pointer;font-size:.78rem;font-weight:700}
          .bethel-growth-tabs button.active,.bethel-growth-ranges button.active{background:rgba(56,189,248,.14);color:#e2e8f0;box-shadow:inset 0 0 0 1px rgba(56,189,248,.28)}
          .bethel-growth-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px;margin:15px 0 12px}
          .bethel-growth-card{padding:12px 13px;border-radius:11px;background:rgba(8,18,33,.66);border:1px solid rgba(148,163,184,.15)}
          .bethel-growth-card small{display:block;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:.045em;font-size:.69rem}
          .bethel-growth-card strong{font-size:1.18rem}
          .bethel-growth-chart-wrap{position:relative;width:100%;overflow:hidden;border-radius:12px;background:linear-gradient(180deg,rgba(5,13,27,.84),rgba(2,6,23,.65));border:1px solid rgba(148,163,184,.13)}
          #bethel-growth-chart{display:block;width:100%;height:390px;cursor:crosshair}
          .bethel-growth-tooltip{position:absolute;display:none;pointer-events:none;z-index:4;min-width:180px;padding:10px 11px;border-radius:9px;background:rgba(2,6,23,.94);border:1px solid rgba(148,163,184,.24);box-shadow:0 12px 32px rgba(0,0,0,.3);font-size:.77rem;color:#cbd5e1}
          .bethel-growth-tooltip strong{display:block;color:#f8fafc;font-size:.86rem;margin-bottom:5px}.bethel-growth-tooltip span{display:block;margin-top:3px}
          .bethel-growth-legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;color:#cbd5e1;font-size:.78rem}
          .bethel-growth-legend span:before{content:"";display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor;border-radius:2px}
          .bethel-growth-note{color:#94a3b8;font-size:.78rem;line-height:1.45;margin-top:10px}
          .bethel-growth-status{font-size:.75rem;color:#94a3b8;margin-top:7px}
          @media(max-width:900px){#bethel-growth-chart{height:320px}.bethel-growth-tools{width:100%}.bethel-growth-ranges{overflow:auto;max-width:100%}}
        `;
        document.head.appendChild(style);
    }

    function buildPanel(){
        const view=document.querySelector("#view-analytics");
        if(!view||document.querySelector("#bethel-performance-growth"))return;
        const panel=document.createElement("article");
        panel.id="bethel-performance-growth";
        panel.className="panel bethel-growth-panel";
        panel.innerHTML=`
          <div class="bethel-growth-head">
            <div><h2>Account Growth & Performance</h2><p>Cash-flow-adjusted return and account-value history for the active master account.</p></div>
            <div class="bethel-growth-tools">
              <div class="bethel-growth-tabs" aria-label="Chart mode">
                <button type="button" data-growth-mode="return" class="active">Return %</button>
                <button type="button" data-growth-mode="equity">Equity / Balance</button>
              </div>
              <button id="bethel-growth-reload" type="button">Refresh chart</button>
            </div>
          </div>
          <div id="bethel-growth-summary" class="bethel-growth-summary"></div>
          <div class="bethel-growth-ranges" aria-label="Chart range">
            <button type="button" data-growth-range="TOTAL" class="active">TOTAL</button>
            <button type="button" data-growth-range="1Y">1Y</button>
            <button type="button" data-growth-range="6M">6M</button>
            <button type="button" data-growth-range="3M">3M</button>
            <button type="button" data-growth-range="1M">1M</button>
            <button type="button" data-growth-range="1W">1W</button>
            <button type="button" data-growth-range="1D">1D</button>
          </div>
          <div class="bethel-growth-chart-wrap">
            <canvas id="bethel-growth-chart" aria-label="Bethel account performance chart"></canvas>
            <div id="bethel-growth-tooltip" class="bethel-growth-tooltip"></div>
          </div>
          <div id="bethel-growth-legend" class="bethel-growth-legend"><span>Cash-flow-adjusted return</span></div>
          <div id="bethel-growth-status" class="bethel-growth-status"></div>
          <p class="bethel-growth-note">Time is plotted on a true calendar scale. Return mode neutralizes recorded deposits and withdrawals between MT5 snapshots; Equity / Balance mode shows the raw account values. No synthetic performance points are generated.</p>
        `;
        const risk=document.querySelector("#bethel-risk-monitor");
        if(risk)view.insertBefore(panel,risk);else view.appendChild(panel);

        document.querySelector("#bethel-growth-reload")?.addEventListener("click",loadGrowth);
        panel.querySelectorAll("[data-growth-mode]").forEach(button=>button.addEventListener("click",()=>{
            state.mode=button.dataset.growthMode;
            panel.querySelectorAll("[data-growth-mode]").forEach(b=>b.classList.toggle("active",b===button));
            updateLegend();applyRange();
        }));
        panel.querySelectorAll("[data-growth-range]").forEach(button=>button.addEventListener("click",()=>{
            state.range=button.dataset.growthRange;
            panel.querySelectorAll("[data-growth-range]").forEach(b=>b.classList.toggle("active",b===button));
            applyRange();
        }));
        const canvas=panel.querySelector("#bethel-growth-chart");
        canvas.addEventListener("mousemove",handleHover);
        canvas.addEventListener("mouseleave",()=>{hideTooltip();drawCurrent();});
    }

    async function loadGrowth(){
        buildPanel();
        const button=document.querySelector("#bethel-growth-reload");
        if(button){button.disabled=true;button.textContent="Refreshing…";}
        setStatus("Loading signed MT5 history…");
        try{
            const [analytics,historyResponse,audit]=await Promise.all([
                window.apiGet("/performance/analytics"),
                window.apiGet("/performance/equity-history"),
                window.apiGet("/performance/analytics-fxblue-banked-return-preview").catch(()=>null)
            ]);
            const account=String(analytics?.master_account||"").trim();
            const historyDays=Number(analytics?.history_days);
            let rows=(historyResponse?.history||[])
                .filter(row=>!account||String(row.account_number||"").trim()===account)
                .map(row=>({...row,_at:parseDate(row.timestamp)}))
                .filter(row=>row._at&&Number.isFinite(Number(row.equity))&&Number(row.equity)>0)
                .sort((a,b)=>a._at-b._at);

            if(rows.length&&Number.isFinite(historyDays)&&historyDays>0){
                const end=rows[rows.length-1]._at;
                const start=new Date(end.getTime()-historyDays*DAY_MS);
                rows=rows.filter(row=>row._at>=start&&row._at<=end);
            }

            state.analytics=analytics||{};
            state.rows=rows;
            state.cashFlows=normalizeCashFlows(audit?.cash_flows||[]);
            state.series=buildSeries(rows,state.cashFlows);
            renderSummary();
            updateRangeAvailability();
            applyRange();
            setStatus(rows.length?`${rows.length.toLocaleString()} signed MT5 snapshots · ${formatDateTime(rows[rows.length-1]._at)} latest`:`No MT5 snapshots available in the account-history window.`);
        }catch(error){
            state.rows=[];state.series=[];state.visible=[];
            const target=document.querySelector("#bethel-growth-summary");
            if(target)target.innerHTML=card("Chart status","Unavailable")+card("Reason",error?.message||"Unable to load account history");
            setStatus("Performance chart unavailable.");
            drawCurrent();
        }finally{
            if(button){button.disabled=false;button.textContent="Refresh chart";}
        }
    }

    function normalizeCashFlows(flows){
        return flows.map(flow=>({
            at:parseDate(flow.occurred_at),
            amount:Number(flow.amount||0)
        })).filter(flow=>flow.at&&Number.isFinite(flow.amount)).sort((a,b)=>a.at-b.at);
    }

    function buildSeries(rows,cashFlows){
        if(!rows.length)return [];
        const out=[];
        let factor=1;
        out.push(pointFromRow(rows[0],0));
        for(let i=1;i<rows.length;i++){
            const prev=rows[i-1],curr=rows[i];
            const prevEq=Number(prev.equity);
            const currEq=Number(curr.equity);
            const externalFlow=cashFlows.reduce((sum,flow)=>flow.at>prev._at&&flow.at<=curr._at?sum+flow.amount:sum,0);
            if(prevEq>0){
                const periodFactor=(currEq-externalFlow)/prevEq;
                if(Number.isFinite(periodFactor)&&periodFactor>0)factor*=periodFactor;
            }
            out.push(pointFromRow(curr,(factor-1)*100));
        }
        return out;
    }

    function pointFromRow(row,returnPct){
        return {at:row._at,equity:Number(row.equity),balance:Number(row.balance||0),returnPct:Number(returnPct)};
    }

    function applyRange(){
        const full=state.series;
        if(!full.length){state.visible=[];drawCurrent();return;}
        if(state.range==="TOTAL")state.visible=full;
        else{
            const end=full[full.length-1].at.getTime();
            const duration=RANGE_MS[state.range]||Infinity;
            const start=end-duration;
            state.visible=full.filter(point=>point.at.getTime()>=start);
            if(!state.visible.length)state.visible=[full[full.length-1]];
        }
        renderRangeReturn();
        drawCurrent();
    }

    function updateRangeAvailability(){
        const panel=document.querySelector("#bethel-performance-growth");if(!panel||!state.series.length)return;
        const span=state.series[state.series.length-1].at-state.series[0].at;
        panel.querySelectorAll("[data-growth-range]").forEach(button=>{
            const range=button.dataset.growthRange;
            button.disabled=range!=="TOTAL"&&span<Math.min(RANGE_MS[range]||0,DAY_MS*.75);
        });
    }

    function renderSummary(){
        const target=document.querySelector("#bethel-growth-summary");if(!target)return;
        const a=state.analytics||{},rows=state.rows;
        if(!rows.length){target.innerHTML=card("Master account",a.master_account||"—")+card("History","No snapshots");return;}
        const first=rows[0],last=rows[rows.length-1];
        target.innerHTML=[
            card("Master account",a.master_account||"—"),
            card("Account history",Number.isFinite(Number(a.history_days))?`${Number(a.history_days).toFixed(1)} days`:durationLabel(first._at,last._at)),
            card("History start",formatDate(first._at)),
            card("History end",formatDate(last._at)),
            card("Current equity",money(last.equity)),
            card("Headline total return",Number.isFinite(Number(a.total_return_percent))?pct(Number(a.total_return_percent)):"—"),
            card("Chart TWR",state.series.length?pct(state.series[state.series.length-1].returnPct):"—"),
            card("Snapshots",rows.length.toLocaleString())
        ].join("");
    }

    function renderRangeReturn(){
        const target=document.querySelector("#bethel-growth-status");if(!target||!state.visible.length)return;
        const first=state.visible[0],last=state.visible[state.visible.length-1];
        let rangeReturn=0;
        if(state.mode==="return"){
            const fullStart=1+first.returnPct/100,fullEnd=1+last.returnPct/100;
            rangeReturn=fullStart>0?((fullEnd/fullStart)-1)*100:0;
            target.textContent=`${state.range} · ${formatDate(first.at)} → ${formatDate(last.at)} · Return ${rangeReturn>=0?"+":""}${rangeReturn.toFixed(2)}% · ${state.visible.length.toLocaleString()} points`;
        }else{
            target.textContent=`${state.range} · ${formatDate(first.at)} → ${formatDate(last.at)} · ${state.visible.length.toLocaleString()} actual MT5 snapshots`;
        }
    }

    function updateLegend(){
        const legend=document.querySelector("#bethel-growth-legend");if(!legend)return;
        legend.innerHTML=state.mode==="return"?"<span>Cash-flow-adjusted return %</span>":"<span>Equity</span><span>Balance</span>";
    }

    function drawCurrent(crosshairIndex=null){
        const canvas=document.querySelector("#bethel-growth-chart");if(!canvas)return;
        const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
        const width=Math.max(520,Math.floor(rect.width||900)),height=Math.max(280,Math.floor(rect.height||390));
        canvas.width=width*dpr;canvas.height=height*dpr;
        const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);ctx.font="12px system-ui";
        const series=state.visible;
        if(!series.length){ctx.fillStyle="#94a3b8";ctx.fillText("No account-history data available for this period.",24,40);state.geometry=null;return;}

        const pad={l:72,r:26,t:24,b:46},plotW=width-pad.l-pad.r,plotH=height-pad.t-pad.b;
        const times=series.map(p=>p.at.getTime()),minTime=Math.min(...times),maxTime=Math.max(...times);
        const values=state.mode==="return"?series.map(p=>p.returnPct):series.flatMap(p=>[p.equity,p.balance]);
        let min=Math.min(...values.filter(Number.isFinite)),max=Math.max(...values.filter(Number.isFinite));
        if(state.mode==="return"){min=Math.min(min,0);max=Math.max(max,0);}
        if(max===min){max+=1;min-=1;}
        const padding=(max-min)*.12||1;min-=padding;max+=padding;
        const xForTime=t=>pad.l+(maxTime===minTime?plotW/2:((t-minTime)/(maxTime-minTime))*plotW);
        const yForValue=v=>pad.t+((max-v)/(max-min))*plotH;
        const x=i=>xForTime(times[i]);

        drawGrid(ctx,{width,height,pad,plotW,plotH,min,max,minTime,maxTime,xForTime,yForValue});

        if(state.mode==="return"){
            const zeroY=yForValue(0);
            ctx.strokeStyle="rgba(226,232,240,.34)";ctx.lineWidth=1.1;ctx.beginPath();ctx.moveTo(pad.l,zeroY);ctx.lineTo(width-pad.r,zeroY);ctx.stroke();
            drawArea(ctx,series,p=>p.returnPct,x,yForValue,zeroY);
            drawLine(ctx,series,p=>p.returnPct,x,yForValue,"#38bdf8",2.35);
        }else{
            drawLine(ctx,series,p=>p.equity,x,yForValue,"#22d3ee",2.45);
            drawLine(ctx,series,p=>p.balance,x,yForValue,"#a78bfa",2.05);
        }

        const last=series[series.length-1];
        const lastValue=state.mode==="return"?last.returnPct:last.equity;
        const lx=x(series.length-1),ly=yForValue(lastValue);
        ctx.fillStyle=state.mode==="return"?"#38bdf8":"#22d3ee";ctx.beginPath();ctx.arc(lx,ly,3.6,0,Math.PI*2);ctx.fill();

        if(Number.isInteger(crosshairIndex)&&series[crosshairIndex]){
            const cx=x(crosshairIndex);
            ctx.strokeStyle="rgba(226,232,240,.42)";ctx.lineWidth=1;ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(cx,pad.t);ctx.lineTo(cx,height-pad.b);ctx.stroke();ctx.setLineDash([]);
            const p=series[crosshairIndex],v=state.mode==="return"?p.returnPct:p.equity,cy=yForValue(v);
            ctx.fillStyle="#f8fafc";ctx.beginPath();ctx.arc(cx,cy,4,0,Math.PI*2);ctx.fill();
        }

        state.geometry={width,height,pad,plotW,plotH,times,minTime,maxTime,xForTime,yForValue,series};
    }

    function drawGrid(ctx,g){
        const horizontal=5,vertical=6;
        ctx.lineWidth=1;
        for(let i=0;i<=horizontal;i++){
            const ratio=i/horizontal,yy=g.pad.t+g.plotH*ratio;
            ctx.strokeStyle="rgba(148,163,184,.13)";ctx.beginPath();ctx.moveTo(g.pad.l,yy);ctx.lineTo(g.width-g.pad.r,yy);ctx.stroke();
            const value=g.max-(g.max-g.min)*ratio;
            ctx.fillStyle="#94a3b8";ctx.textAlign="right";ctx.textBaseline="middle";
            ctx.fillText(state.mode==="return"?`${value.toFixed(Math.abs(value)<10?2:1)}%`:compactMoney(value),g.pad.l-10,yy);
        }
        for(let i=0;i<=vertical;i++){
            const ratio=i/vertical,time=g.minTime+(g.maxTime-g.minTime)*ratio,xx=g.xForTime(time);
            ctx.strokeStyle="rgba(148,163,184,.09)";ctx.beginPath();ctx.moveTo(xx,g.pad.t);ctx.lineTo(xx,g.height-g.pad.b);ctx.stroke();
            ctx.fillStyle="#94a3b8";ctx.textAlign=i===0?"left":i===vertical?"right":"center";ctx.textBaseline="top";
            ctx.fillText(formatAxisDate(new Date(time),g.maxTime-g.minTime),xx,g.height-g.pad.b+12);
        }
        ctx.textAlign="left";ctx.textBaseline="alphabetic";
    }

    function drawArea(ctx,series,getValue,x,y,zeroY){
        if(series.length<2)return;
        const gradient=ctx.createLinearGradient(0,0,0,ctx.canvas.clientHeight||390);
        gradient.addColorStop(0,"rgba(56,189,248,.20)");gradient.addColorStop(1,"rgba(56,189,248,.015)");
        ctx.beginPath();ctx.moveTo(x(0),zeroY);
        series.forEach((p,i)=>ctx.lineTo(x(i),y(Number(getValue(p)))));
        ctx.lineTo(x(series.length-1),zeroY);ctx.closePath();ctx.fillStyle=gradient;ctx.fill();
    }

    function drawLine(ctx,series,getValue,x,y,color,width){
        ctx.beginPath();let started=false;
        series.forEach((p,i)=>{
            const v=Number(getValue(p));if(!Number.isFinite(v))return;
            const xx=x(i),yy=y(v);if(!started){ctx.moveTo(xx,yy);started=true;}else ctx.lineTo(xx,yy);
        });
        ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();
    }

    function handleHover(event){
        const g=state.geometry;if(!g||!g.series.length)return;
        const canvas=event.currentTarget,rect=canvas.getBoundingClientRect();
        const mouseX=event.clientX-rect.left;
        if(mouseX<g.pad.l||mouseX>g.width-g.pad.r){hideTooltip();drawCurrent();return;}
        const targetTime=g.minTime+((mouseX-g.pad.l)/g.plotW)*(g.maxTime-g.minTime);
        let index=0,best=Infinity;
        g.times.forEach((time,i)=>{const distance=Math.abs(time-targetTime);if(distance<best){best=distance;index=i;}});
        drawCurrent(index);
        showTooltip(g.series[index],event.clientX-rect.left,event.clientY-rect.top,rect.width);
    }

    function showTooltip(point,x,y,width){
        const tip=document.querySelector("#bethel-growth-tooltip");if(!tip)return;
        tip.innerHTML=state.mode==="return"?
            `<strong>${escapeText(formatDateTime(point.at))}</strong><span>Return: <b>${point.returnPct>=0?"+":""}${point.returnPct.toFixed(2)}%</b></span><span>Equity: ${escapeText(money(point.equity))}</span><span>Balance: ${escapeText(money(point.balance))}</span>`:
            `<strong>${escapeText(formatDateTime(point.at))}</strong><span>Equity: <b>${escapeText(money(point.equity))}</b></span><span>Balance: ${escapeText(money(point.balance))}</span><span>Cash-flow-adjusted return: ${point.returnPct>=0?"+":""}${point.returnPct.toFixed(2)}%</span>`;
        tip.style.display="block";
        const left=Math.min(Math.max(8,x+14),Math.max(8,width-205));
        tip.style.left=`${left}px`;tip.style.top=`${Math.max(8,y-25)}px`;
    }

    function hideTooltip(){const tip=document.querySelector("#bethel-growth-tooltip");if(tip)tip.style.display="none";}
    function setStatus(text){const target=document.querySelector("#bethel-growth-status");if(target)target.textContent=text;}
    function card(label,value){return `<div class="bethel-growth-card"><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong></div>`;}
    function normalizeTimestamp(value){const text=String(value||"").trim();if(!text)return text;if(/[zZ]$|[+-]\d\d:?\d\d$/.test(text))return text;return text.replace(" ","T")+"Z";}
    function parseDate(value){if(!value)return null;const d=new Date(normalizeTimestamp(value));return Number.isNaN(d.getTime())?null:d;}
    function formatDate(d){return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});}
    function formatDateTime(d){return d.toLocaleString("en-GB",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit",timeZone:"UTC"})+" UTC";}
    function formatAxisDate(d,span){if(span<=2*DAY_MS)return d.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",timeZone:"UTC"});if(span<=62*DAY_MS)return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",timeZone:"UTC"});return d.toLocaleDateString("en-GB",{month:"short",year:"2-digit",timeZone:"UTC"});}
    function durationLabel(a,b){return `${Math.max(0,(b-a)/DAY_MS).toFixed(1)} days`;}
    function money(v){try{return new Intl.NumberFormat("en",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(v));}catch{return Number(v).toFixed(2);}}
    function compactMoney(v){return "$"+new Intl.NumberFormat("en",{notation:"compact",maximumFractionDigits:1}).format(Number(v));}
    function pct(v){return `${Number(v).toFixed(2)}%`;}
    function escapeText(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

    waitForRuntime();
})();
