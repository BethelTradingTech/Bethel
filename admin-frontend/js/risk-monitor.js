/*
Bethel Trading Technologies
Super Admin Institutional Risk Analysis

Visible values are sourced only from /performance/analytics for the dynamically
resolved active master. Internal engine diagnostics are intentionally not shown.
*/
(function(){
    "use strict";

    const POLL_MS = 100;
    const MAX_WAIT_MS = 10000;
    let initialized = false;
    let lastHistory = [];

    function waitForAdminRuntime(){
        const started = Date.now();
        const timer = setInterval(()=>{
            if(typeof window.apiGet === "function" && document.querySelector("#view-analytics")){
                clearInterval(timer);
                initialize();
            }else if(Date.now()-started > MAX_WAIT_MS){
                clearInterval(timer);
            }
        },POLL_MS);
    }

    function initialize(){
        if(initialized) return;
        initialized = true;
        injectStyles();
        buildWorkspace();
        document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(loadRisk,50));
        document.querySelector("#refresh-button")?.addEventListener("click",()=>{
            if(document.querySelector("#view-analytics")?.classList.contains("active")) setTimeout(loadRisk,100);
        });
        if(document.querySelector("#view-analytics")?.classList.contains("active")) loadRisk();
    }

    function injectStyles(){
        if(document.querySelector("#bethel-risk-monitor-style")) return;
        const style=document.createElement("style");
        style.id="bethel-risk-monitor-style";
        style.textContent=`
            .bethel-risk-shell{display:grid;gap:18px;margin-top:18px}
            .bethel-risk-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
            .bethel-risk-card{background:rgba(8,18,33,.72);border:1px solid rgba(148,163,184,.18);border-radius:14px;padding:14px;min-height:88px}
            .bethel-risk-card small{display:block;color:#94a3b8;margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em;font-size:.72rem}
            .bethel-risk-card strong{display:block;font-size:1.35rem;line-height:1.2}
            .bethel-risk-panel{background:rgba(8,18,33,.62);border:1px solid rgba(148,163,184,.16);border-radius:14px;padding:16px}
            .bethel-risk-chart{width:100%;height:330px;display:block;background:rgba(2,6,23,.45);border-radius:10px}
            .bethel-risk-legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;color:#cbd5e1;font-size:.8rem}
            .bethel-risk-legend span:before{content:"";display:inline-block;width:12px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor}
            @media(max-width:900px){.bethel-risk-chart{height:280px}}
        `;
        document.head.appendChild(style);
    }

    function buildWorkspace(){
        const view=document.querySelector("#view-analytics");
        if(!view||document.querySelector("#bethel-risk-monitor")) return;
        const shell=document.createElement("div");
        shell.id="bethel-risk-monitor";
        shell.className="bethel-risk-shell";
        shell.innerHTML=`
            <article class="panel">
                <div class="section-heading">
                    <div><h2>Institutional Risk Analysis</h2></div>
                    <button id="bethel-risk-reload" type="button">Refresh risk</button>
                </div>
                <div id="bethel-risk-metrics" class="bethel-risk-metrics"></div>
            </article>
            <article class="bethel-risk-panel">
                <h3>Historical Risk Chart</h3>
                <canvas id="bethel-risk-chart" class="bethel-risk-chart"></canvas>
                <div class="bethel-risk-legend"><span>Equity</span><span>Drawdown %</span></div>
            </article>
        `;
        view.appendChild(shell);
        document.querySelector("#bethel-risk-reload")?.addEventListener("click",loadRisk);
    }

    async function loadRisk(){
        buildWorkspace();
        setLoading(true);
        try{
            const [analytics,history]=await Promise.all([
                window.apiGet("/performance/analytics"),
                window.apiGet("/performance/equity-history")
            ]);
            const a=analytics||{};
            lastHistory=selectActiveMasterHistory(history?.history||[],a.master_account);
            renderMetrics(a);
            drawRiskChart(buildHistoricalSeries(lastHistory));
        }finally{
            setLoading(false);
        }
    }

    function setLoading(loading){
        const button=document.querySelector("#bethel-risk-reload");
        if(!button) return;
        button.disabled=loading;
        button.textContent=loading?"Refreshing…":"Refresh risk";
    }

    function metric(label,value){
        return `<div class="bethel-risk-card"><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong></div>`;
    }

    function renderMetrics(a){
        const target=document.querySelector("#bethel-risk-metrics");
        if(!target) return;
        target.innerHTML=[
            metric("Monthly VaR (95%)",pct(a.value_at_risk_95_percent)),
            metric("Expected Shortfall (95%)",pct(a.expected_shortfall_95_percent)),
            metric("Maximum Drawdown",pct(a.maximum_drawdown_percent)),
            metric("Recovery Factor",numberOrDash(a.recovery_factor)),
            metric("Sharpe Ratio",numberOrDash(a.sharpe_ratio)),
            metric("Sortino Ratio",numberOrDash(a.sortino_ratio)),
            metric("Calmar Ratio",numberOrDash(a.calmar_ratio)),
            metric("Volatility",pct(a.volatility)),
            metric("Consistency Score",numberOrDash(a.consistency_score)),
            metric("Risk Score",numberOrDash(a.risk_score)),
            metric("Risk Level",String(a.risk_level||"—")),
            metric("Performance Score",numberOrDash(a.performance_score)),
            metric("Performance Grade",String(a.performance_grade||"—")),
            metric("Master Account",String(a.master_account||"—"))
        ].join("");
    }

    function selectActiveMasterHistory(rows,account){
        const wanted=String(account||"").trim();
        return rows
            .filter(row=>!wanted||String(row.account_number||"").trim()===wanted)
            .filter(row=>isFiniteNumber(row.equity)&&Number(row.equity)>0&&row.timestamp)
            .sort((a,b)=>new Date(a.timestamp)-new Date(b.timestamp));
    }

    function buildHistoricalSeries(rows){
        const dailyMap=new Map();
        rows.forEach(row=>{
            const date=String(row.timestamp).slice(0,10);
            dailyMap.set(date,{date,equity:Number(row.equity)});
        });
        const daily=[...dailyMap.values()].sort((a,b)=>a.date.localeCompare(b.date));
        if(!daily.length) return [];
        let peak=daily[0].equity;
        return daily.map(point=>{
            peak=Math.max(peak,point.equity);
            return {date:point.date,equity:point.equity,drawdown:peak>0?((peak-point.equity)/peak)*100:0};
        });
    }

    function drawRiskChart(series){
        const canvas=document.querySelector("#bethel-risk-chart");
        if(!canvas) return;
        const rect=canvas.getBoundingClientRect();
        const dpr=window.devicePixelRatio||1;
        const width=Math.max(480,Math.floor(rect.width||900));
        const height=Math.max(260,Math.floor(rect.height||330));
        canvas.width=width*dpr; canvas.height=height*dpr;
        const ctx=canvas.getContext("2d");
        ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,width,height);
        if(series.length<2) return;

        const pad={left:52,right:48,top:22,bottom:34};
        const plotW=width-pad.left-pad.right, plotH=height-pad.top-pad.bottom;
        const equities=series.map(x=>x.equity);
        const eqMin=Math.min(...equities),eqMax=Math.max(...equities);
        const ddMax=Math.max(1,...series.map(x=>x.drawdown));
        const xAt=i=>pad.left+(i/(series.length-1))*plotW;
        const yEq=v=>pad.top+(1-((v-eqMin)/Math.max(eqMax-eqMin,1e-9)))*plotH;
        const yDd=v=>pad.top+(1-(v/ddMax))*plotH;

        ctx.strokeStyle="rgba(148,163,184,.16)"; ctx.lineWidth=1;
        for(let i=0;i<=4;i++){
            const y=pad.top+(i/4)*plotH;
            ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(width-pad.right,y);ctx.stroke();
        }
        drawLine(ctx,series,xAt,p=>yEq(p.equity),"#22c55e",2);
        drawLine(ctx,series,xAt,p=>yDd(p.drawdown),"#ef4444",1.7);

        ctx.font="11px sans-serif";ctx.fillStyle="#94a3b8";
        ctx.fillText(moneyUSD(eqMin),pad.left,height-10);
        ctx.textAlign="right";ctx.fillText(series[series.length-1].date,width-pad.right,height-10);ctx.textAlign="left";
    }

    function drawLine(ctx,series,xAt,yAt,color,width){
        ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();
        series.forEach((point,index)=>{const x=xAt(index),y=yAt(point);index?ctx.lineTo(x,y):ctx.moveTo(x,y);});
        ctx.stroke();
    }

    function number(value){const n=Number(value);return Number.isFinite(n)?n:null;}
    function isFiniteNumber(value){return number(value)!==null;}
    function pct(value){const n=number(value);return n===null?"—":`${n.toFixed(2)}%`;}
    function numberOrDash(value){const n=number(value);return n===null?"—":n.toFixed(2);}
    function moneyUSD(value){const n=number(value);return n===null?"—":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(n);}
    function escapeText(value){return String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));}

    window.addEventListener("resize",()=>{
        if(lastHistory.length&&document.querySelector("#view-analytics")?.classList.contains("active")) drawRiskChart(buildHistoricalSeries(lastHistory));
    });

    if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",waitForAdminRuntime,{once:true});
    else waitForAdminRuntime();
})();
