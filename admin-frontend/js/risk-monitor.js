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
    const AUTO_REFRESH_MS = 15000;
    let initialized = false;
    let lastHistory = [];
    let refreshTimer = null;
    let loading = false;

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
        refreshTimer = window.setInterval(()=>{
            if(document.querySelector("#view-analytics")?.classList.contains("active")) loadRisk();
        },AUTO_REFRESH_MS);
        if(document.querySelector("#view-analytics")?.classList.contains("active")) loadRisk();
    }

    function injectStyles(){
        if(document.querySelector("#bethel-risk-monitor-style")) return;
        const style=document.createElement("style");
        style.id="bethel-risk-monitor-style";
        style.textContent=`
            .bethel-risk-shell{display:grid;gap:18px;margin-top:18px}
            .bethel-risk-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:14px}
            .bethel-risk-card{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(8,18,33,.92),rgba(15,23,42,.84));border:1px solid rgba(148,163,184,.18);border-radius:16px;padding:16px;min-height:96px;box-shadow:0 10px 28px rgba(2,6,23,.20);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
            .bethel-risk-card:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(2,6,23,.28)}
            .bethel-risk-card:before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:#64748b}
            .bethel-risk-card small{display:block;color:#94a3b8;margin-bottom:9px;text-transform:uppercase;letter-spacing:.055em;font-size:.70rem;font-weight:700}
            .bethel-risk-card strong{display:block;font-size:1.45rem;line-height:1.15;color:#f8fafc;font-weight:750;letter-spacing:-.02em}
            .bethel-risk-card.tone-blue{border-color:rgba(59,130,246,.30)}
            .bethel-risk-card.tone-blue:before{background:#3b82f6}
            .bethel-risk-card.tone-blue strong{color:#bfdbfe}
            .bethel-risk-card.tone-cyan{border-color:rgba(34,211,238,.30)}
            .bethel-risk-card.tone-cyan:before{background:#22d3ee}
            .bethel-risk-card.tone-cyan strong{color:#a5f3fc}
            .bethel-risk-card.tone-amber{border-color:rgba(245,158,11,.32)}
            .bethel-risk-card.tone-amber:before{background:#f59e0b}
            .bethel-risk-card.tone-amber strong{color:#fde68a}
            .bethel-risk-card.tone-green{border-color:rgba(34,197,94,.34)}
            .bethel-risk-card.tone-green:before{background:#22c55e}
            .bethel-risk-card.tone-green strong{color:#bbf7d0}
            .bethel-risk-card.tone-purple{border-color:rgba(168,85,247,.32)}
            .bethel-risk-card.tone-purple:before{background:#a855f7}
            .bethel-risk-card.tone-purple strong{color:#e9d5ff}
            .bethel-risk-card.tone-red{border-color:rgba(239,68,68,.38)}
            .bethel-risk-card.tone-red:before{background:#ef4444}
            .bethel-risk-card.tone-red strong{color:#fecaca}
            .bethel-risk-card.tone-orange{border-color:rgba(249,115,22,.36)}
            .bethel-risk-card.tone-orange:before{background:#f97316}
            .bethel-risk-card.tone-orange strong{color:#fed7aa}
            .bethel-risk-panel{background:linear-gradient(145deg,rgba(8,18,33,.78),rgba(15,23,42,.70));border:1px solid rgba(148,163,184,.16);border-radius:16px;padding:16px;box-shadow:0 12px 30px rgba(2,6,23,.18)}
            .bethel-risk-chart{width:100%;height:330px;display:block;background:rgba(2,6,23,.45);border-radius:12px}
            .bethel-risk-legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;color:#cbd5e1;font-size:.8rem}
            .bethel-risk-legend span:before{content:"";display:inline-block;width:12px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor}
            #bethel-risk-reload{border:1px solid rgba(59,130,246,.35);background:linear-gradient(135deg,rgba(37,99,235,.92),rgba(59,130,246,.78));color:#fff;border-radius:10px;padding:9px 14px;font-weight:700;box-shadow:0 7px 18px rgba(37,99,235,.20)}
            #bethel-risk-reload:disabled{opacity:.65;cursor:wait}
            @media(max-width:900px){.bethel-risk-chart{height:280px}.bethel-risk-metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}}
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
        if(loading) return;
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
        }catch(error){
            console.error("Unable to refresh Institutional Risk Analysis",error);
        }finally{
            setLoading(false);
        }
    }

    function setLoading(state){
        loading=state;
        const button=document.querySelector("#bethel-risk-reload");
        if(!button) return;
        button.disabled=state;
        button.textContent=state?"Refreshing…":"Refresh risk";
    }

    function metric(label,value,tone){
        return `<div class="bethel-risk-card ${escapeText(tone||"tone-blue")}"><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong></div>`;
    }

    function riskTone(value){
        const level=String(value||"").trim().toUpperCase();
        if(level==="LOW") return "tone-green";
        if(level==="MODERATE") return "tone-amber";
        if(level==="ELEVATED") return "tone-orange";
        if(level==="HIGH") return "tone-red";
        return "tone-blue";
    }

    function gradeTone(value){
        const grade=String(value||"").trim().toUpperCase();
        if(grade.startsWith("A")) return "tone-green";
        if(grade.startsWith("B")) return "tone-cyan";
        if(grade.startsWith("C")) return "tone-amber";
        if(grade) return "tone-orange";
        return "tone-blue";
    }

    function renderMetrics(a){
        const target=document.querySelector("#bethel-risk-metrics");
        if(!target) return;
        target.innerHTML=[
            metric("Monthly VaR (95%)",pct(a.value_at_risk_95_percent),"tone-blue"),
            metric("Expected Shortfall (95%)",pct(a.expected_shortfall_95_percent),"tone-purple"),
            metric("Maximum Drawdown",pct(a.maximum_drawdown_percent),"tone-amber"),
            metric("Recovery Factor",numberOrDash(a.recovery_factor),"tone-cyan"),
            metric("Sharpe Ratio",numberOrDash(a.sharpe_ratio),"tone-green"),
            metric("Sortino Ratio",numberOrDash(a.sortino_ratio),"tone-green"),
            metric("Calmar Ratio",numberOrDash(a.calmar_ratio),"tone-cyan"),
            metric("Volatility",pct(a.volatility),"tone-amber"),
            metric("Consistency Score",numberOrDash(a.consistency_score),"tone-purple"),
            metric("Risk Score",numberOrDash(a.risk_score),riskTone(a.risk_level)),
            metric("Risk Level",String(a.risk_level||"—"),riskTone(a.risk_level)),
            metric("Performance Score",numberOrDash(a.performance_score),gradeTone(a.performance_grade)),
            metric("Performance Grade",String(a.performance_grade||"—"),gradeTone(a.performance_grade)),
            metric("Master Account",String(a.master_account||"—"),"tone-purple")
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

    window.addEventListener("beforeunload",()=>{if(refreshTimer) window.clearInterval(refreshTimer);});

    if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",waitForAdminRuntime,{once:true});
    else waitForAdminRuntime();
})();
