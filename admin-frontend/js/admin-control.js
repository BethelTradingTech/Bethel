if(typeof requireAuthentication==="function"&&!requireAuthentication()){throw new Error("Authentication required")}
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const money=v=>new Intl.NumberFormat("en-BB",{style:"currency",currency:"BBD"}).format(Number(v||0));
const titles={overview:"Overview",website:"Website Management",investors:"Investor Management",subscribers:"Subscriber Management",mt5:"MT5 Accounts",copytrading:"Copy Trading",analytics:"Performance & Analytics",api:"API & Routes",security:"Security",settings:"System Settings"};
function showView(name){$$(".view").forEach(x=>x.classList.remove("active"));$$(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.view===name));$("#view-"+name).classList.add("active");$("#page-title").textContent=titles[name];closeMenu();if(name==="api")loadRoutes()}
function openMenu(){$("#sidebar").classList.add("open");$("#overlay").classList.add("show")}function closeMenu(){$("#sidebar").classList.remove("open");$("#overlay").classList.remove("show")}
$$(".nav-item").forEach(b=>b.onclick=()=>showView(b.dataset.view));$$("[data-go]").forEach(b=>b.onclick=()=>showView(b.dataset.go));$("#menu-button").onclick=openMenu;$("#overlay").onclick=closeMenu;$("#logout-button").onclick=()=>typeof logout==="function"?logout():localStorage.clear();
function setStatus(t,error=false){$("#save-status").textContent=t;$("#save-status").style.color=error?"#ef4444":"#10b981";setTimeout(()=>$("#save-status").textContent="",3500)}
function fillForm(form,data){Object.entries(data||{}).forEach(([k,v])=>{const el=form.elements[k];if(!el)return;if(el.type==="checkbox")el.checked=!!v;else el.value=v??""})}
function formData(form){const out={};[...form.elements].forEach(el=>{if(!el.name)return;out[el.name]=el.type==="checkbox"?el.checked:el.value});return out}
async function loadOverview(){
 const [health,account,positions,subscribers,copy,performance]=await Promise.allSettled([apiGet("/health"),apiGet("/mt5/account"),apiGet("/mt5/positions"),apiGet("/copytrading/subscribers"),apiGet("/copytrading/dashboard"),apiGet("/performance/analytics")]);
 $("#system-health").textContent=health.status==="fulfilled"?"ONLINE":"OFFLINE";
 const a=account.status==="fulfilled"?account.value:{};$("#mt5-status").textContent=a.status||a.connection_status||"CONNECTED";$("#balance").textContent=money(a.balance);$("#equity").textContent=money(a.equity);
 const p=positions.status==="fulfilled"?(Array.isArray(positions.value)?positions.value:(positions.value.positions||[])):[];$("#position-count").textContent=p.length;
 const s=subscribers.status==="fulfilled"?(Array.isArray(subscribers.value)?subscribers.value:(subscribers.value.subscribers||[])):[];$("#subscriber-count").textContent=s.length;
 renderSubscribers(s);renderPositions(p);renderDetails("#mt5-details",a);if(copy.status==="fulfilled")renderDetails("#copy-details",copy.value);if(performance.status==="fulfilled")renderDetails("#performance-details",performance.value);
 try{const inv=await apiGet("/admin/investors");renderInvestors(inv.investors||inv||[])}catch(e){$("#investors-table").innerHTML='<tr><td colspan="5">Investor API unavailable</td></tr>'}
}
function renderDetails(selector,obj){const el=$(selector);if(!el)return;el.innerHTML=Object.entries(obj||{}).filter(([,v])=>typeof v!=="object").slice(0,20).map(([k,v])=>`<div><small>${k.replaceAll("_"," ")}</small><strong>${v??"—"}</strong></div>`).join("")||"<p>No data available.</p>"}
function renderSubscribers(rows){$("#subscribers-table").innerHTML=rows.map(r=>`<tr><td>${r.id??""}</td><td>${r.name??""}</td><td>${r.email??""}</td><td>${r.mt5_account||r.account_number||""}</td><td>${r.status||""}</td></tr>`).join("")||'<tr><td colspan="5">No subscribers found.</td></tr>'}
function renderPositions(rows){$("#positions-table").innerHTML=rows.map(r=>`<tr><td>${r.symbol||""}</td><td>${r.type||r.direction||""}</td><td>${r.volume??""}</td><td>${r.profit??""}</td></tr>`).join("")||'<tr><td colspan="4">No open positions.</td></tr>'}
function renderInvestors(rows){$("#investors-table").innerHTML=rows.map(r=>`<tr><td>${r.name||r.full_name||""}</td><td>${r.email||""}</td><td>${r.status||""}</td><td>${r.portfolio_value??r.current_value??"—"}</td><td><button type="button">View</button></td></tr>`).join("")||'<tr><td colspan="5">No investors found.</td></tr>'}
async function loadSettings(){try{const data=await apiGet("/admin/control/settings");fillForm($("#website-form"),data.website);fillForm($("#system-form"),data.system)}catch(e){setStatus(e.message,true)}}
$("#website-form").onsubmit=async e=>{e.preventDefault();try{await apiPut("/admin/control/settings/website",formData(e.currentTarget));setStatus("Website settings saved")}catch(err){setStatus(err.message,true)}}
$("#system-form").onsubmit=async e=>{e.preventDefault();try{await apiPut("/admin/control/settings/system",formData(e.currentTarget));setStatus("System settings saved")}catch(err){setStatus(err.message,true)}}
async function loadRoutes(){try{const data=await apiGet("/admin/control/routes");window.routeRows=data.routes||[];renderRoutes(window.routeRows)}catch(e){$("#routes-table").innerHTML=`<tr><td colspan="4">${e.message}</td></tr>`}}
function renderRoutes(rows){$("#routes-table").innerHTML=rows.map(r=>`<tr><td>${r.methods.join(", ")}</td><td>${r.path}</td><td>${r.name}</td><td>ONLINE</td></tr>`).join("")}
$("#route-search").oninput=e=>{const q=e.target.value.toLowerCase();renderRoutes((window.routeRows||[]).filter(r=>(r.path+" "+r.name+" "+r.methods.join(" ")).toLowerCase().includes(q)))}
$("#load-routes").onclick=loadRoutes;$("#refresh-button").onclick=()=>{loadOverview();loadSettings()};loadOverview();loadSettings();
