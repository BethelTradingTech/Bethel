const API_BASE=(location.hostname==="localhost"||location.hostname==="127.0.0.1")?"http://127.0.0.1:8000":(location.hostname==="bethel-api.onrender.com"||location.hostname==="api.betheltradingtechnologies.com")?location.origin:"https://bethel-api.onrender.com";
function getToken(){return localStorage.getItem("bethel_access_token")}
async function apiRequest(endpoint,options={}){
 const headers={Accept:"application/json",...(options.headers||{})};const token=getToken();if(token)headers.Authorization="Bearer "+token;
 if(options.body&&!headers["Content-Type"])headers["Content-Type"]="application/json";
 const response=await fetch(API_BASE+endpoint,{credentials:"include",...options,headers});
 if(response.status===401||response.status===403)throw new Error("Administrator authorization required");
 const type=response.headers.get("content-type")||"";const data=type.includes("application/json")?await response.json():await response.text();
 if(!response.ok)throw new Error(data.detail||data||("API error "+response.status));return data;
}
const apiGet=e=>apiRequest(e);
const apiPost=(e,data)=>apiRequest(e,{method:"POST",body:data===undefined?undefined:JSON.stringify(data)});
const apiPut=(e,data)=>apiRequest(e,{method:"PUT",body:JSON.stringify(data)});
const apiPatch=(e,data)=>apiRequest(e,{method:"PATCH",body:JSON.stringify(data)});

const PERFORMANCE_FIELD_ORDER=[
 "status","master_account","analytics_method","baseline_source","starting_capital","funding_base","deposits","withdrawals",
 "current_balance","current_equity","floating_profit_loss","closed_profit","total_profit","total_return_percent",
 "banked_return_percent","daily_return_percent","weekly_return_percent","monthly_return_percent","history_days",
 "profit_factor","total_trades","winning_trades","losing_trades","breakeven_trades","win_rate","gross_profit",
 "gross_loss","average_win","average_loss","payoff_ratio","expectancy","sharpe_ratio","sortino_ratio",
 "recovery_factor","maximum_drawdown_amount","maximum_drawdown_percent","volatility","calmar_ratio",
 "value_at_risk_95_amount","value_at_risk_95_percent","consistency_score","risk_level","performance_grade",
 "cash_flow_events","snapshots_analyzed"
];

function normalizedReturnsFromBankedReturn(bankedReturnPercent,tradingWeekdays){
 const days=Number(tradingWeekdays);
 const total=Number(bankedReturnPercent)/100;
 if(!Number.isFinite(days)||days<=0||!Number.isFinite(total)||total<=-1)return null;
 const dailyFactor=Math.pow(1+total,1/days);
 return {
  daily_return_percent:(dailyFactor-1)*100,
  weekly_return_percent:(Math.pow(dailyFactor,5)-1)*100,
  monthly_return_percent:(Math.pow(dailyFactor,21)-1)*100
 };
}

function countWeekdaysInclusive(startValue,endValue){
 const start=new Date(startValue);const end=new Date(endValue);
 if(Number.isNaN(start.getTime())||Number.isNaN(end.getTime())||end<start)return 0;
 let count=0;const current=new Date(start.getFullYear(),start.getMonth(),start.getDate());
 const last=new Date(end.getFullYear(),end.getMonth(),end.getDate());
 while(current<=last){const day=current.getDay();if(day!==0&&day!==6)count+=1;current.setDate(current.getDate()+1)}
 return count;
}

function buildSuperAdminPerformance(stable,audit){
 const merged={...(stable||{})};
 if(!audit||audit.status!=="available"||!Number.isFinite(Number(audit.banked_return_percent)))return merged;
 const historyStart=audit.cash_flows?.[0]?.occurred_at||audit.subperiods?.[0]?.start_at;
 const historyEnd=audit.subperiods?.[audit.subperiods.length-1]?.end_at;
 const tradingWeekdays=countWeekdaysInclusive(historyStart,historyEnd);
 const normalized=normalizedReturnsFromBankedReturn(audit.banked_return_percent,tradingWeekdays);
 merged.analytics_method="FX Blue-style cash-flow-split compounded banked return";
 merged.banked_return_percent=Number(audit.banked_return_percent).toFixed(2);
 if(normalized){
  merged.daily_return_percent=normalized.daily_return_percent.toFixed(2);
  merged.weekly_return_percent=normalized.weekly_return_percent.toFixed(2);
  merged.monthly_return_percent=normalized.monthly_return_percent.toFixed(2);
 }
 return merged;
}

function performanceValueColor(key,value){
 const colors={
  total_return_percent:"#22c55e",banked_return_percent:"#10b981",daily_return_percent:"#38bdf8",
  weekly_return_percent:"#a78bfa",monthly_return_percent:"#f59e0b",current_balance:"#60a5fa",
  current_equity:"#22d3ee",closed_profit:"#22c55e",total_profit:"#34d399",profit_factor:"#10b981",
  win_rate:"#3b82f6",gross_profit:"#22c55e",gross_loss:"#ef4444",average_win:"#4ade80",
  average_loss:"#fb7185",maximum_drawdown_amount:"#ef4444",maximum_drawdown_percent:"#f43f5e",
  value_at_risk_95_amount:"#dc2626",value_at_risk_95_percent:"#dc2626",volatility:"#fb923c",
  sharpe_ratio:"#c084fc",sortino_ratio:"#a855f7",calmar_ratio:"#fbbf24",consistency_score:"#60a5fa",
  expectancy:"#c084fc",recovery_factor:"#14b8a6",performance_grade:"#3b82f6",risk_level:"#ef4444"
 };
 if(key==="floating_profit_loss")return Number(value)>=0?"#22c55e":"#ef4444";
 if(key==="risk_level"){
  const risk=String(value||"").toUpperCase();
  if(risk==="LOW")return "#22c55e";
  if(risk==="MEDIUM")return "#f59e0b";
  if(risk==="CRITICAL")return "#dc2626";
  return "#ef4444";
 }
 if(key==="performance_grade"){
  const grade=String(value||"").toUpperCase();
  if(grade.startsWith("A"))return "#22c55e";
  if(grade.startsWith("B"))return "#3b82f6";
  if(grade.startsWith("C"))return "#f59e0b";
  if(grade.startsWith("D"))return "#fb923c";
  if(grade.startsWith("F"))return "#ef4444";
 }
 return colors[key]||"";
}

function renderCompletePerformance(data){
 const target=document.querySelector("#performance-details");
 if(!target)return;
 const ordered=[];
 const seen=new Set();
 for(const key of PERFORMANCE_FIELD_ORDER){
  if(Object.prototype.hasOwnProperty.call(data,key)&&typeof data[key]!=="object"){
   ordered.push([key,data[key]]);seen.add(key);
  }
 }
 for(const [key,value] of Object.entries(data||{})){
  if(!seen.has(key)&&typeof value!=="object")ordered.push([key,value]);
 }
 target.innerHTML=ordered.map(([key,value])=>{
  const color=performanceValueColor(key,value);
  const style=color?` style="color:${color}"`:"";
  return `<div><small>${key.replaceAll("_"," ")}</small><strong${style}>${value??"—"}</strong></div>`;
 }).join("")||"<p>No data available.</p>";
}

async function refreshCompletePerformance(){
 const analyticsView=document.querySelector("#view-analytics");
 if(!analyticsView||!analyticsView.classList.contains("active"))return;
 try{
  const [stable,audit]=await Promise.all([
   apiGet("/performance/analytics"),
   apiGet("/performance/analytics-fxblue-banked-return-preview")
  ]);
  renderCompletePerformance(buildSuperAdminPerformance(stable,audit));
 }
 catch(error){
  const target=document.querySelector("#performance-details");
  if(target)target.innerHTML=`<p class="notice">${String(error.message||"Performance analytics unavailable")}</p>`;
 }
}

window.apiGet=apiGet;

window.addEventListener("DOMContentLoaded",()=>{
 document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(refreshCompletePerformance,50));
 document.querySelector('#refresh-button')?.addEventListener("click",()=>setTimeout(refreshCompletePerformance,50));
 setInterval(refreshCompletePerformance,60000);
 const nativeReviewScript=document.createElement("script");
 nativeReviewScript.src="/admin-frontend/js/admin-kyc-review.js?v=1";
 nativeReviewScript.defer=true;
 document.head.appendChild(nativeReviewScript);
});
