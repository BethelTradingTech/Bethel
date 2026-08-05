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
 "status","master_account","baseline_source","starting_capital","funding_base","deposits","withdrawals",
 "current_balance","current_equity","floating_profit_loss","closed_profit","total_profit","total_return_percent",
 "banked_return_percent","daily_return_percent","weekly_return_percent","monthly_return_percent","history_days",
 "profit_factor","total_trades","winning_trades","losing_trades","breakeven_trades","win_rate","gross_profit",
 "gross_loss","average_win","average_loss","payoff_ratio","expectancy","sharpe_ratio","sortino_ratio",
 "recovery_factor","maximum_drawdown_amount","maximum_drawdown_percent","volatility","calmar_ratio",
 "value_at_risk_95_amount","value_at_risk_95_percent","consistency_score","risk_level","performance_grade",
 "cash_flow_events","snapshots_analyzed"
];

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
 target.innerHTML=ordered.map(([key,value])=>`<div><small>${key.replaceAll("_"," ")}</small><strong>${value??"—"}</strong></div>`).join("")||"<p>No data available.</p>";
}

async function refreshCompletePerformance(){
 const analyticsView=document.querySelector("#view-analytics");
 if(!analyticsView||!analyticsView.classList.contains("active"))return;
 try{renderCompletePerformance(await apiGet("/performance/analytics"));}
 catch(error){
  const target=document.querySelector("#performance-details");
  if(target)target.innerHTML=`<p class="notice">${String(error.message||"Performance analytics unavailable")}</p>`;
 }
}

window.addEventListener("DOMContentLoaded",()=>{
 document.querySelector('[data-view="analytics"]')?.addEventListener("click",()=>setTimeout(refreshCompletePerformance,50));
 document.querySelector('#refresh-button')?.addEventListener("click",()=>setTimeout(refreshCompletePerformance,50));
 setInterval(refreshCompletePerformance,60000);
});
