/*
Bethel Trading Technologies
Super Admin Risk Monitor

This file extends only the protected Super Admin Performance view. It does not
modify investor/subscriber-facing pages or trading execution.
*/
(function(){
    "use strict";

    const POLL_MS = 100;
    const MAX_WAIT_MS = 10000;
    const ALERT_THRESHOLDS = Object.freeze({
        drawdown_percent: 5,
        monthly_var_percent: 8,
        recovery_factor: 1
    });

    let initialized = false;
    let lastAnalytics = null;
    let lastHistory = [];

    function waitForAdminRuntime(){
        const started = Date.now();
        const timer = setInterval(()=>{
            if(typeof window.apiGet === "function" && document.querySelector("#view-analytics")){
                clearInterval(timer);
                initialize();
            } else if(Date.now() - started > MAX_WAIT_MS){
                clearInterval(timer);
                console.warn("Bethel Risk Monitor: admin runtime was not available in time.");
            }
        }, POLL_MS);
    }

    function initialize(){
        if(initialized) return;
        initialized = true;
        injectStyles();
        buildRiskWorkspace();

        const analyticsNav = document.querySelector('[data-view="analytics"]');
        if(analyticsNav){
            analyticsNav.addEventListener("click", ()=>setTimeout(loadRiskMonitor, 50));
        }

        const refresh = document.querySelector("#refresh-button");
        if(refresh){
            refresh.addEventListener("click", ()=>{
                if(document.querySelector("#view-analytics")?.classList.contains("active")){
                    setTimeout(loadRiskMonitor, 100);
                }
            });
        }

        if(document.querySelector("#view-analytics")?.classList.contains("active")){
            loadRiskMonitor();
        }
    }

    function injectStyles(){
        if(document.querySelector("#bethel-risk-monitor-style")) return;
        const style = document.createElement("style");
        style.id = "bethel-risk-monitor-style";
        style.textContent = `
            .bethel-risk-shell{display:grid;gap:18px;margin-top:18px}
            .bethel-risk-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
            .bethel-risk-card{background:rgba(8,18,33,.72);border:1px solid rgba(148,163,184,.18);border-radius:14px;padding:14px;min-height:94px}
            .bethel-risk-card small{display:block;color:#94a3b8;margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em;font-size:.72rem}
            .bethel-risk-card strong{display:block;font-size:1.35rem;line-height:1.2}
            .bethel-risk-sub{margin-top:6px;color:#94a3b8;font-size:.78rem}
            .bethel-risk-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:16px}
            .bethel-risk-panel{background:rgba(8,18,33,.62);border:1px solid rgba(148,163,184,.16);border-radius:14px;padding:16px}
            .bethel-risk-panel h3{margin:0 0 6px}
            .bethel-risk-panel p{margin:0 0 14px;color:#94a3b8}
            .bethel-risk-chart-wrap{width:100%;overflow:hidden}
            .bethel-risk-chart{width:100%;height:330px;display:block;background:rgba(2,6,23,.45);border-radius:10px}
            .bethel-risk-legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;color:#cbd5e1;font-size:.8rem}
            .bethel-risk-legend span:before{content:"";display:inline-block;width:12px;height:3px;margin-right:6px;vertical-align:middle;background:currentColor}
            .bethel-risk-alerts{display:grid;gap:10px}
            .bethel-risk-alert{border-radius:10px;padding:11px 12px;border:1px solid rgba(148,163,184,.18);background:rgba(15,23,42,.64)}
            .bethel-risk-alert strong{display:block;margin-bottom:3px}
            .bethel-risk-alert small{color:#cbd5e1}
            .bethel-risk-alert.ok{border-color:rgba(16,185,129,.35)}
            .bethel-risk-alert.warning{border-color:rgba(245,158,11,.45)}
            .bethel-risk-alert.critical{border-color:rgba(239,68,68,.5)}
            .bethel-risk-alert.info{border-color:rgba(59,130,246,.4)}
            .bethel-risk-quality{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-top:12px}
            .bethel-risk-quality div{padding:9px 10px;border-radius:9px;background:rgba(15,23,42,.55)}
            .bethel-risk-quality small{display:block;color:#94a3b8}
            .bethel-risk-quality strong{display:block;margin-top:3px}
            .bethel-risk-note{font-size:.8rem;color:#94a3b8;margin-top:10px}
            @media (max-width:900px){.bethel-risk-grid{grid-template-columns:1fr}.bethel-risk-chart{height:280px}}
        `;
        document.head.appendChild(style);
    }

    function buildRiskWorkspace(){
        const view = document.querySelector("#view-analytics");
        if(!view || document.querySelector("#bethel-risk-monitor")) return;
        const shell = document.createElement("div");
        shell.id = "bethel-risk-monitor";
        shell.className = "bethel-risk-shell";
        shell.innerHTML = `
            <article class="panel">
                <div class="section-heading">
                    <div>
                        <h2>Institutional Risk Analysis</h2>
                        <p>Super Admin only. Uses the active master account and signed MT5 analytics.</p>
                    </div>
                    <button id="bethel-risk-reload" type="button">Refresh risk</button>
                </div>
                <div id="bethel-risk-metrics" class="bethel-risk-metrics"></div>
                <div id="bethel-risk-quality" class="bethel-risk-quality"></div>
                <p class="bethel-risk-note">Headline VaR is the audited 95% monthly Monte Carlo model. Historical chart VaR is a separate rolling 30-day historical estimate for trend monitoring only.</p>
            </article>
            <div class="bethel-risk-grid">
                <article class="bethel-risk-panel">
                    <h3>Historical Risk Chart</h3>
                    <p>Equity, drawdown, rolling 30-day volatility and rolling historical VaR.</p>
                    <div class="bethel-risk-chart-wrap"><canvas id="bethel-risk-chart" class="bethel-risk-chart"></canvas></div>
                    <div class="bethel-risk-legend">
                        <span>Equity</span><span>Drawdown %</span><span>30d Volatility %</span><span>30d Historical VaR 95%</span>
                    </div>
                </article>
                <article class="bethel-risk-panel">
                    <h3>Risk Monitor & Alerts</h3>
                    <p>Warnings are monitoring signals only and never place, close, or resize trades.</p>
                    <div id="bethel-risk-alerts" class="bethel-risk-alerts"></div>
                </article>
            </div>
        `;
        view.appendChild(shell);
        document.querySelector("#bethel-risk-reload")?.addEventListener("click", loadRiskMonitor);
    }

    async function loadRiskMonitor(){
        buildRiskWorkspace();
        setLoading(true);
        try{
            const [analytics, history] = await Promise.all([
                window.apiGet("/performance/analytics"),
                window.apiGet("/performance/equity-history")
            ]);
            lastAnalytics = analytics || {};
            lastHistory = selectActiveMasterHistory(history?.history || [], lastAnalytics.master_account);
            renderMetrics(lastAnalytics);
            renderQuality(lastAnalytics, lastHistory);
            const series = buildHistoricalSeries(lastHistory);
            renderAlerts(lastAnalytics, series);
            drawRiskChart(series);
        }catch(error){
            const alerts = document.querySelector("#bethel-risk-alerts");
            if(alerts){
                alerts.innerHTML = `<div class="bethel-risk-alert critical"><strong>Risk analytics unavailable</strong><small>${escapeText(error?.message || "Unable to load protected performance analytics")}</small></div>`;
            }
        }finally{
            setLoading(false);
        }
    }

    function setLoading(loading){
        const button = document.querySelector("#bethel-risk-reload");
        if(button){
            button.disabled = loading;
            button.textContent = loading ? "Refreshing…" : "Refresh risk";
        }
    }

    function metric(label, value, sub){
        return `<div class="bethel-risk-card"><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong>${sub ? `<div class="bethel-risk-sub">${escapeText(sub)}</div>` : ""}</div>`;
    }

    function renderMetrics(a){
        const target = document.querySelector("#bethel-risk-metrics");
        if(!target) return;
        const varAvailable = a.var_status === "available" && isFiniteNumber(a.value_at_risk_95_percent);
        const esAvailable = a.var_status === "available" && isFiniteNumber(a.expected_shortfall_95_percent);
        target.innerHTML = [
            metric("Monthly VaR (95%)", varAvailable ? pct(a.value_at_risk_95_percent) : "Unavailable", varAvailable ? "21-trading-day horizon" : varReason(a)),
            metric("Expected Shortfall (95%)", esAvailable ? pct(a.expected_shortfall_95_percent) : "Unavailable", "Average tail loss beyond VaR"),
            metric("Maximum Drawdown", pct(a.maximum_drawdown_percent), isFiniteNumber(a.maximum_drawdown_amount) ? moneyUSD(a.maximum_drawdown_amount) : ""),
            metric("Recovery Factor", numberOrDash(a.recovery_factor), "Profit recovery vs drawdown"),
            metric("Sharpe Ratio", numberOrDash(a.sharpe_ratio), "Risk-adjusted return"),
            metric("Sortino Ratio", numberOrDash(a.sortino_ratio), "Downside-risk adjusted"),
            metric("Calmar Ratio", numberOrDash(a.calmar_ratio), "Return vs max drawdown"),
            metric("Volatility", pct(a.volatility), "Annualized equity volatility"),
            metric("Risk Level", String(a.risk_level || "—"), "Existing Bethel risk classification"),
            metric("Performance Grade", String(a.performance_grade || "—"), `Master ${a.master_account || "—"}`)
        ].join("");
    }

    function renderQuality(a, history){
        const target = document.querySelector("#bethel-risk-quality");
        if(!target) return;
        const available = Number(a.var_available_exposed_days ?? 0);
        const required = Number(a.var_required_exposed_days ?? 45);
        target.innerHTML = [
            quality("VaR engine", a.var_status || "not_available"),
            quality("Confidence", isFiniteNumber(a.var_confidence_percent) ? pct(a.var_confidence_percent) : "95%"),
            quality("Exposed days", `${available}/${required}`),
            quality("Scenarios", Number(a.var_scenario_count || 0).toLocaleString()),
            quality("Snapshots", Number(a.snapshots_analyzed || history.length || 0).toLocaleString()),
            quality("History points", history.length.toLocaleString())
        ].join("");
    }

    function quality(label, value){
        return `<div><small>${escapeText(label)}</small><strong>${escapeText(value)}</strong></div>`;
    }

    function selectActiveMasterHistory(rows, account){
        const wanted = String(account || "").trim();
        const filtered = wanted ? rows.filter(row=>String(row.account_number || "").trim() === wanted) : rows;
        return filtered
            .filter(row=>isFiniteNumber(row.equity) && Number(row.equity) > 0 && row.timestamp)
            .sort((a,b)=>new Date(a.timestamp) - new Date(b.timestamp));
    }

    function buildHistoricalSeries(rows){
        const dailyMap = new Map();
        rows.forEach(row=>{
            const date = String(row.timestamp).slice(0,10);
            dailyMap.set(date, {
                date,
                equity:Number(row.equity),
                balance:Number(row.balance || 0)
            });
        });
        const daily = [...dailyMap.values()].sort((a,b)=>a.date.localeCompare(b.date));
        if(!daily.length) return [];

        let peak = daily[0].equity;
        const returns = [];
        return daily.map((point,index)=>{
            peak = Math.max(peak, point.equity);
            const drawdown = peak > 0 ? ((peak - point.equity) / peak) * 100 : 0;
            let ret = null;
            if(index > 0 && daily[index-1].equity > 0){
                ret = (point.equity / daily[index-1].equity) - 1;
                if(Number.isFinite(ret)) returns.push(ret);
            }
            const recent = returns.slice(-30);
            const volatility = recent.length >= 2 ? sampleStd(recent) * Math.sqrt(252) * 100 : null;
            const historicalVar = recent.length >= 5 ? Math.max(0, -percentile(recent, 5) * 100) : null;
            return {date:point.date,equity:point.equity,drawdown,volatility,historicalVar};
        });
    }

    function renderAlerts(a, series){
        const target = document.querySelector("#bethel-risk-alerts");
        if(!target) return;
        const alerts = [];
        const dd = number(a.maximum_drawdown_percent);
        const var95 = number(a.value_at_risk_95_percent);
        const recovery = number(a.recovery_factor);
        const riskLevel = String(a.risk_level || "").toUpperCase();

        if(a.var_status !== "available"){
            alerts.push({level:"info",title:"VaR history building",text:varReason(a)});
        } else if(var95 !== null && var95 >= ALERT_THRESHOLDS.monthly_var_percent){
            alerts.push({level:"warning",title:"Elevated monthly VaR",text:`Monthly VaR is ${var95.toFixed(2)}%, above the Super Admin monitoring threshold of ${ALERT_THRESHOLDS.monthly_var_percent.toFixed(0)}%.`});
        }

        if(dd !== null && dd >= ALERT_THRESHOLDS.drawdown_percent){
            alerts.push({level:"warning",title:"Drawdown threshold exceeded",text:`Maximum drawdown is ${dd.toFixed(2)}%. Review leverage, exposure and current positions.`});
        }

        if(recovery !== null && recovery < ALERT_THRESHOLDS.recovery_factor){
            alerts.push({level:"warning",title:"Low recovery factor",text:`Recovery factor is ${recovery.toFixed(2)}, below 1.00.`});
        }

        if(riskLevel === "HIGH"){
            alerts.push({level:"critical",title:"Bethel risk level HIGH",text:"The existing Bethel risk classifier is currently HIGH."});
        }

        const vols = series.map(x=>x.volatility).filter(Number.isFinite);
        if(vols.length >= 10){
            const current = vols[vols.length-1];
            const baseline = median(vols.slice(0,-1));
            if(baseline > 0 && current >= baseline * 2){
                alerts.push({level:"warning",title:"Volatility expansion",text:`Rolling volatility is more than twice its historical median (${current.toFixed(2)}% vs ${baseline.toFixed(2)}%).`});
            }
        }

        if(!alerts.length){
            alerts.push({level:"ok",title:"No active risk warnings",text:"Current monitored metrics are within the configured Super Admin thresholds."});
        }

        target.innerHTML = alerts.map(item=>`<div class="bethel-risk-alert ${item.level}"><strong>${escapeText(item.title)}</strong><small>${escapeText(item.text)}</small></div>`).join("");
    }

    function drawRiskChart(series){
        const canvas = document.querySelector("#bethel-risk-chart");
        if(!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const width = Math.max(480, Math.floor(rect.width || 900));
        const height = Math.max(260, Math.floor(rect.height || 330));
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        const ctx = canvas.getContext("2d");
        ctx.setTransform(dpr,0,0,dpr,0,0);
        ctx.clearRect(0,0,width,height);

        if(series.length < 2){
            ctx.fillStyle = "#94a3b8";
            ctx.font = "14px sans-serif";
            ctx.fillText("Not enough master-account history to draw the risk chart.", 18, 32);
            return;
        }

        const pad = {left:52,right:48,top:22,bottom:34};
        const plotW = width - pad.left - pad.right;
        const plotH = height - pad.top - pad.bottom;
        const equities = series.map(x=>x.equity);
        const eqMin = Math.min(...equities);
        const eqMax = Math.max(...equities);
        const riskValues = series.flatMap(x=>[x.drawdown,x.volatility,x.historicalVar]).filter(Number.isFinite);
        const riskMax = Math.max(1, ...riskValues);
        const xAt = i=>pad.left + (i/(series.length-1))*plotW;
        const yEq = v=>pad.top + (1 - ((v-eqMin)/Math.max(eqMax-eqMin,1e-9)))*plotH;
        const yRisk = v=>pad.top + (1 - (v/riskMax))*plotH;

        ctx.strokeStyle = "rgba(148,163,184,.16)";
        ctx.lineWidth = 1;
        for(let i=0;i<=4;i++){
            const y = pad.top + (i/4)*plotH;
            ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(width-pad.right,y);ctx.stroke();
        }

        drawLine(ctx,series,xAt,p=>yEq(p.equity),"#22c55e",2);
        drawLine(ctx,series,xAt,p=>yRisk(p.drawdown),"#ef4444",1.7);
        drawLine(ctx,series,xAt,p=>Number.isFinite(p.volatility)?yRisk(p.volatility):null,"#3b82f6",1.5);
        drawLine(ctx,series,xAt,p=>Number.isFinite(p.historicalVar)?yRisk(p.historicalVar):null,"#f59e0b",1.5);

        ctx.font = "11px sans-serif";
        ctx.fillStyle = "#94a3b8";
        ctx.fillText(`Equity ${moneyUSD(eqMin)} – ${moneyUSD(eqMax)}`, pad.left, height-10);
        const endLabel = series[series.length-1].date;
        ctx.textAlign = "right";
        ctx.fillText(endLabel, width-pad.right, height-10);
        ctx.textAlign = "left";
        ctx.fillText(`${riskMax.toFixed(1)}% risk scale`, width-pad.right-96, 14);
    }

    function drawLine(ctx, series, xAt, yAt, color, width){
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        let started = false;
        series.forEach((point,index)=>{
            const y = yAt(point);
            if(!Number.isFinite(y)){started=false;return;}
            const x = xAt(index);
            if(!started){ctx.moveTo(x,y);started=true;}else{ctx.lineTo(x,y);}
        });
        ctx.stroke();
    }

    function sampleStd(values){
        if(values.length < 2) return 0;
        const mean = values.reduce((a,b)=>a+b,0)/values.length;
        const variance = values.reduce((sum,v)=>sum + ((v-mean)**2),0)/(values.length-1);
        return Math.sqrt(Math.max(0,variance));
    }

    function percentile(values, p){
        if(!values.length) return 0;
        const sorted = [...values].sort((a,b)=>a-b);
        const index = (p/100)*(sorted.length-1);
        const lower = Math.floor(index), upper = Math.ceil(index);
        if(lower === upper) return sorted[lower];
        const weight = index-lower;
        return sorted[lower]*(1-weight)+sorted[upper]*weight;
    }

    function median(values){
        if(!values.length) return 0;
        return percentile(values,50);
    }

    function number(value){
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }
    function isFiniteNumber(value){return number(value) !== null;}
    function pct(value){const n=number(value);return n===null?"—":`${n.toFixed(2)}%`;}
    function numberOrDash(value){const n=number(value);return n===null?"—":n.toFixed(2);}
    function moneyUSD(value){const n=number(value);return n===null?"—":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(n);}
    function varReason(a){
        if(a.var_reason) return String(a.var_reason).replaceAll("_"," ");
        const available = Number(a.var_available_exposed_days ?? 0);
        const required = Number(a.var_required_exposed_days ?? 45);
        if(available < required) return `${available} of ${required} exposed days available`;
        return "Audited VaR is not currently available";
    }
    function escapeText(value){
        return String(value ?? "").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    }

    window.addEventListener("resize", ()=>{
        if(lastHistory.length && document.querySelector("#view-analytics")?.classList.contains("active")){
            drawRiskChart(buildHistoricalSeries(lastHistory));
        }
    });

    if(document.readyState === "loading"){
        document.addEventListener("DOMContentLoaded", waitForAdminRuntime, {once:true});
    }else{
        waitForAdminRuntime();
    }
})();
