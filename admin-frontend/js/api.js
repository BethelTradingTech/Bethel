const API_BASE=(location.hostname==="localhost"||location.hostname==="127.0.0.1")?"http://127.0.0.1:8000":"https://api.betheltradingtechnologies.com";
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
const apiPut=(e,data)=>apiRequest(e,{method:"PUT",body:JSON.stringify(data)});
