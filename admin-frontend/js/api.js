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

// The legacy dashboard renderer capped detail panels at 20 scalar fields. Override
// it after admin-control.js loads so the complete production analytics response is
// visible without changing any connector, account, trading, or calculation logic.
setTimeout(()=>{
 window.renderDetails=(selector,obj)=>{
  const el=document.querySelector(selector);
  if(!el)return;
  const rows=Object.entries(obj||{}).filter(([,value])=>typeof value!=="object");
  el.innerHTML=rows.map(([key,value])=>`<div><small>${key.replaceAll("_"," ")}</small><strong>${value??"—"}</strong></div>`).join("")||"<p>No data available.</p>";
 };
 if(document.querySelector("#view-analytics")?.classList.contains("active")&&typeof window.loadAnalytics==="function")window.loadAnalytics();
},0);
