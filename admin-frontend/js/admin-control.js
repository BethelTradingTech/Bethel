if(typeof requireAuthentication==="function"&&!requireAuthentication()){throw new Error("Authentication required")}
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const money=v=>new Intl.NumberFormat("en-BB",{style:"currency",currency:"BBD"}).format(Number(v||0));
const titles={overview:"Overview",website:"Website Management",investors:"Investor Management",subscribers:"Subscriber Management",operations:"Backup & Security",operations:"Backup & Security",notifications:"Notifications",legal:"Legal Consent",profitshare:"20% Profit Split",subscriptions:"Subscription Lifecycle",payments:"Payment Reconciliation",mt5:"MT5 Accounts",copytrading:"Copy Trading",analytics:"Performance & Analytics",api:"API & Routes",security:"Security",settings:"System Settings"};
function showView(name){$$(".view").forEach(x=>x.classList.remove("active"));$$(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.view===name));$("#view-"+name).classList.add("active");$("#page-title").textContent=titles[name];closeMenu();if(name==="api")loadRoutes();if(name==="payments")loadPayments();if(name==="subscriptions")loadSubscriptions();if(name==="profitshare")loadProfitShareAdmin();if(name==="legal")loadLegalAdmin();if(name==="notifications")loadNotifications();if(name==="operations")loadOperations();if(name==="analytics")loadAnalytics();if(name==="copytrading")loadCopyHub()}
function openMenu(){$("#sidebar").classList.add("open");$("#overlay").classList.add("show")}function closeMenu(){$("#sidebar").classList.remove("open");$("#overlay").classList.remove("show")}
$$(".nav-item").forEach(b=>b.onclick=()=>showView(b.dataset.view));$$("[data-go]").forEach(b=>b.onclick=()=>showView(b.dataset.go));$("#menu-button").onclick=openMenu;$("#overlay").onclick=closeMenu;$("#logout-button").onclick=()=>typeof logout==="function"?logout():localStorage.clear();
function setStatus(t,error=false){$("#save-status").textContent=t;$("#save-status").style.color=error?"#ef4444":"#10b981";setTimeout(()=>$("#save-status").textContent="",3500)}
function fillForm(form,data){Object.entries(data||{}).forEach(([k,v])=>{const el=form.elements[k];if(!el)return;if(el.type==="checkbox")el.checked=!!v;else el.value=v??""})}
function formData(form){const out={};[...form.elements].forEach(el=>{if(!el.name)return;out[el.name]=el.type==="checkbox"?el.checked:el.value});return out}
async function loadOverview(){
 const [health,account,positions,subscribers,copy,performance,connector]=await Promise.allSettled([apiGet("/health"),apiGet("/mt5/account"),apiGet("/mt5/positions"),apiGet("/copytrading/subscribers"),apiGet("/copytrading/dashboard"),apiGet("/performance/analytics"),apiGet("/connector/v1/status")]);
 $("#system-health").textContent=health.status==="fulfilled"?"ONLINE":"OFFLINE";
 const c=connector.status==="fulfilled"?connector.value:{status:"OFFLINE",connectors:[]};renderConnectorStatus(c);
 const live=c.connectors?.[0];const a=live||(account.status==="fulfilled"?account.value:{});$("#mt5-status").textContent=c.status||a.status||a.connection_status||"OFFLINE";$("#balance").textContent=money(a.balance);$("#equity").textContent=money(a.equity);
 const p=live?.open_positions||(positions.status==="fulfilled"?(Array.isArray(positions.value)?positions.value:(positions.value.positions||[])):[]);$("#position-count").textContent=p.length;
 const s=subscribers.status==="fulfilled"?(Array.isArray(subscribers.value)?subscribers.value:(subscribers.value.subscribers||[])):[];$("#subscriber-count").textContent=s.length;
 await renderSubscribers(s);renderPositions(p);renderDetails("#mt5-details",a);if(copy.status==="fulfilled")renderDetails("#copy-details",copy.value);if(performance.status==="fulfilled")renderDetails("#performance-details",performance.value);
 try{const inv=await apiGet("/admin/investors");renderInvestors(inv.investors||inv||[])}catch(e){$("#investors-table").innerHTML='<tr><td colspan="5">Investor API unavailable</td></tr>'}
}
function renderConnectorStatus(data){
 const badge=$("#connector-badge"),target=$("#connector-details"),alert=$("#connector-alert"),item=data.connectors?.[0];
 const status=data.status||"OFFLINE";badge.textContent=status;badge.className="connector-badge status-"+status.toLowerCase();
 alert.hidden=status==="ONLINE";alert.textContent=status==="STALE"?"Warning: MT5 connector data is stale. Check the laptop, internet connection and MT5 terminal.":"Critical: MT5 connector is offline. Performance and positions are not updating.";
 if(!item){target.innerHTML='<p class="notice">No signed connector snapshot has been received.</p>';return}
 const rows=[["Account",item.account_number],["Server",item.server],["Mode",item.account_mode],["Last seen",new Date(item.last_seen).toLocaleString()],["Balance",money(item.balance)],["Equity",money(item.equity)],["Floating P/L",money(item.floating_profit)],["Execution","READ ONLY"]];
 target.innerHTML=rows.map(([label,value])=>`<div><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("");
}
async function loadAnalytics(){
 const target=$("#performance-details");
 target.innerHTML="<p>Loading performance analytics...</p>";
 try{
  const data=await apiGet("/performance/analytics");
  renderDetails("#performance-details",data);
 }catch(error){
  target.innerHTML=`<p class="notice">${escapeHtml(error.message||"Performance analytics unavailable")}</p>`;
 }
}

async function loadCopyHub(){
 const table=$("#copyhub-table");if(!table)return;
 try{
  const data=await apiGet("/copyhub/v1/admin/status");window.copyHubState=data;
  $("#copyhub-master").textContent=`Master ${data.master_account}`;
  const globalStatus=data.operational_status||"UNKNOWN";
  $("#copyhub-global-state").textContent=globalStatus;
  $("#copyhub-global-state").className=`review-state state-${String(globalStatus).toLowerCase().replaceAll("_","-")}`;
  $("#copyhub-global-toggle").textContent=data.globally_paused?"Resume all copying":"Emergency pause";
  table.innerHTML=(data.receivers||[]).map(row=>{
   const heartbeat=row.last_heartbeat_at?new Date(row.last_heartbeat_at+"Z"):null;
   const primaryAction=row.active?"deactivate":"activate";
   const primaryAllowed=row.active?row.can_deactivate:row.can_activate;
   const pauseAction=row.paused?"resume":"pause";
   const pauseAllowed=row.paused?row.can_resume:row.can_pause;
   return `<tr><td>${escapeHtml(row.receiver_id)}</td><td><strong>${escapeHtml(row.account_number)}</strong></td><td>${stateBadge(row.environment)}</td><td>${escapeHtml(row.currency_unit)} · ${row.is_cent_account?"CENT":"STANDARD"}</td><td>${stateBadge(row.connection_status)}<br><small>${heartbeat?heartbeat.toLocaleString():"Never connected"}</small></td><td>${stateBadge(row.copy_status)}</td><td><div class="review-actions"><button data-copyhub-action="${primaryAction}" data-receiver="${escapeHtml(row.receiver_id)}" data-account="${escapeHtml(row.account_number)}" ${primaryAllowed?"":"disabled"}>${row.active?"Deactivate":"Activate"}</button><button data-copyhub-action="${pauseAction}" data-receiver="${escapeHtml(row.receiver_id)}" ${pauseAllowed?"":"disabled"}>${row.paused?"Resume":"Pause"}</button></div></td></tr>`;
  }).join("")||'<tr><td colspan="7">No copier receivers have been provisioned.</td></tr>';
  $$('[data-copyhub-action]').forEach(button=>button.onclick=()=>handleCopyHubAction(button));
 }catch(error){table.innerHTML=`<tr><td colspan="7">${escapeHtml(error.message)}</td></tr>`}
}

async function handleCopyHubAction(button){
 const action=button.dataset.copyhubAction,receiver=button.dataset.receiver,account=button.dataset.account;
 button.disabled=true;
 try{
  if(action==="activate"||action==="deactivate"){
   const active=action==="activate",confirmation=`${active?"ACTIVATE":"DEACTIVATE"} RECEIVER ${account}`;
   if(prompt(`Type exactly: ${confirmation}`)!==confirmation)return;
   await apiPatch(`/copyhub/v1/admin/receivers/${encodeURIComponent(receiver)}/activation`,{active,confirmation});
  }else await apiPatch(`/copyhub/v1/admin/receivers/${encodeURIComponent(receiver)}/pause`,{paused:action==="pause"});
  await loadCopyHub();
 }catch(error){setStatus(error.message,true)}finally{button.disabled=false}
}

$("#reload-copyhub").onclick=loadCopyHub;
$("#copyhub-global-toggle").onclick=async()=>{
 const paused=!window.copyHubState?.globally_paused;
 if(paused&&!confirm("Emergency-pause copying for every subscriber?"))return;
 if(!paused&&prompt("Type RESUME ALL COPYING")!=="RESUME ALL COPYING")return;
 try{await apiPatch("/copyhub/v1/admin/global-pause",{paused});await loadCopyHub()}catch(error){setStatus(error.message,true)}
};
function renderDetails(selector,obj){const el=$(selector);if(!el)return;el.innerHTML=Object.entries(obj||{}).filter(([,v])=>typeof v!=="object").slice(0,20).map(([k,v])=>`<div><small>${k.replaceAll("_"," ")}</small><strong>${v??"â€”"}</strong></div>`).join("")||"<p>No data available.</p>"}
const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const stateBadge=value=>`<span class="review-state state-${String(value||"UNKNOWN").toLowerCase().replaceAll("_","-")}">${escapeHtml(value||"UNKNOWN")}</span>`;

const createSubscriberForm=$("#create-subscriber-form");
if(createSubscriberForm)createSubscriberForm.addEventListener("submit",async event=>{
 const form=event.currentTarget,button=form.querySelector('button[type="submit"]'),result=$("#create-subscriber-result");
 event.preventDefault();button.disabled=true;button.textContent="Creating secure setup link…";result.textContent="";
 try{
  const payload={name:form.elements.name.value.trim(),email:form.elements.email.value.trim().toLowerCase(),account_number:form.elements.account_number.value.trim(),allocation_percent:Number(form.elements.allocation_percent.value)};
  const subscriber=await apiPost("/copytrading/subscribers",payload);
  const invite=await apiPost(`/admin/subscribers/${subscriber.id}/invite`,{});
  result.textContent=`Subscriber ${subscriber.id} created. The one-time setup link expires in 24 hours.`;
  if(navigator.clipboard)await navigator.clipboard.writeText(invite.setup_url).catch(()=>{});
  window.prompt("Copy this secure one-time setup link:",invite.setup_url);
  form.reset();form.elements.allocation_percent.value="100";await loadOverview();
 }catch(error){result.textContent=error.message||"Unable to create subscriber";setStatus(result.textContent,true)}
 finally{button.disabled=false;button.textContent="Create Subscriber & Setup Link"}
});






async function renderSubscribers(rows){
 const results=await Promise.all(rows.map(async subscriber=>{
  try{return {subscriber,onboarding:await apiGet(`/onboarding/${subscriber.id}`)}}
  catch(error){return {subscriber,onboarding:{error:error.message}}}
 }));
 window.subscriberReviews=new Map(results.map(item=>[Number(item.subscriber.id),item]));
 $("#subscribers-table").innerHTML=results.map(({subscriber:r,onboarding:o})=>{
  if(o.error)return `<tr><td><strong>${escapeHtml(r.name)}</strong><br><small>${escapeHtml(r.email)}</small></td><td colspan="5">${escapeHtml(o.error)}</td><td><button class="review-action" data-action="refresh" data-id="${r.id}">Retry</button></td></tr>`;
  const paymentReference=o.payment_reference?`<small>${escapeHtml(o.payment_reference)}</small>`:"";
  const account=o.broker_account||null;
  const accountDetails=account?`<br><small>${escapeHtml(account.platform)} · ${escapeHtml(account.account_type||"STANDARD")} · ${escapeHtml(account.broker)} · ${escapeHtml(account.login)}</small><br><small>Starting capital: ${Number(account.starting_capital_usd||0).toFixed(2)} · ${account.capital_verified?"Verified":"Not verified"}</small><br>${stateBadge(account.live_authorized?"LIVE AUTHORIZED":"PAPER ONLY")}`:"";
  return `<tr>
   <td><strong>${escapeHtml(r.name)}</strong><br><small>ID ${r.id} - ${escapeHtml(r.email)}</small></td>
   <td>${stateBadge(o.subscription_status)}</td>
   <td>${stateBadge(o.kyc_status)}</td>
   <td>${stateBadge(o.payment_status)}${paymentReference}</td>
   <td>${stateBadge(o.broker_status)}${accountDetails}</td>
   <td>${stateBadge(o.admin_approval)}<br>${stateBadge(o.copy_trading_status)}</td>
   <td><div class="review-actions">
    <button data-action="setup-invite" data-id="${r.id}">Create Setup Link</button>\n    <button data-action="kyc-approve" data-id="${r.id}" ${o.kyc_status!=="PENDING"?"disabled":""}>Approve KYC</button>
    <button data-action="kyc-reject" data-id="${r.id}" ${o.kyc_status!=="PENDING"?"disabled":""}>Reject KYC</button>
    <button data-action="payment-confirm" data-id="${r.id}" ${o.payment_status!=="PENDING_VERIFICATION"?"disabled":""}>Verify Payment</button>
    <button data-action="broker-refresh" data-id="${r.id}">Verify MT5</button>
    <button data-action="approval-approve" data-id="${r.id}" ${o.admin_approval==="APPROVED"?"disabled":""}>Approve Activation</button>
    <button data-action="approval-reject" data-id="${r.id}">Reject</button>
    <button data-action="copier-code" data-id="${r.id}" data-account-id="${account?.id||""}" ${!account?"disabled":""}>Create Copier Code</button>
    <button data-action="live-enable" data-id="${r.id}" data-account-id="${account?.id||""}" ${!account||account.platform!=="MT5"||o.copy_trading_status!=="ACTIVE"||account.live_authorized?"disabled":""}>Enable Live MT5</button>
    <button class="danger-button" data-action="live-disable" data-id="${r.id}" data-account-id="${account?.id||""}" ${!account?.live_authorized?"disabled":""}>Emergency Stop</button>
    <button class="danger-button" data-action="delete-subscriber" data-id="${r.id}" ${r.status==="ACTIVE"||r.payment_status==="PAID"?"disabled":""}>Delete Permanently</button>
   </div></td>
  </tr>`;
 }).join("")||'<tr><td colspan="7">No subscribers found.</td></tr>';
 $$("#subscribers-table [data-action]").forEach(button=>button.onclick=()=>handleReviewAction(button));
}

async function handleReviewAction(button){
 const id=Number(button.dataset.id), action=button.dataset.action;
 const item=window.subscriberReviews?.get(id), onboarding=item?.onboarding||{};
 if(action==="setup-invite"){
    button.disabled=true;
    try{
      const data=await apiPost(`/admin/subscribers/${id}/invite`,{});
      if(navigator.clipboard)await navigator.clipboard.writeText(data.setup_url);
      window.prompt("Copy this one-time subscriber setup link:",data.setup_url);
      setStatus("Subscriber setup link created");
    }catch(error){setStatus(error.message||"Unable to create setup link",true)}
    finally{button.disabled=false}
    return;
  }
  if(action==="refresh"){await loadOverview();return}
 if(action==="delete-subscriber"){
  const confirmation=`DELETE SUBSCRIBER ${id}`;
  if(prompt(`This permanently deletes this unpaid, inactive subscriber. Type exactly: ${confirmation}`)!==confirmation)return;
  button.disabled=true;
  try{await apiRequest(`/copytrading/subscribers/${id}`,{method:"DELETE",body:JSON.stringify({confirmation})});setStatus("Subscriber permanently deleted");await loadOverview()}
  catch(error){setStatus(error.message||"Unable to delete subscriber",true)}finally{button.disabled=false}
  return;
 }
 let endpoint="", payload;
 if(action==="kyc-approve"){
  if(!confirm(`Approve KYC for subscriber ${id}?`))return;
  endpoint=`/onboarding/${id}/kyc/review`;payload={decision:"APPROVED"};
 }else if(action==="kyc-reject"){
  const reason=prompt("Reason for rejecting KYC:");if(!reason)return;
  endpoint=`/onboarding/${id}/kyc/review`;payload={decision:"REJECTED",reason};
 }else if(action==="payment-confirm"){
  if(!onboarding.payment_reference){setStatus("No payment reference submitted",true);return}
  if(!confirm(`Verify payment reference ${onboarding.payment_reference}?`))return;
  endpoint=`/onboarding/${id}/payment/confirm`;payload={reference:onboarding.payment_reference};
 }else if(action==="broker-refresh"){
  endpoint=`/onboarding/${id}/broker/refresh`;payload=undefined;
 }else if(action==="approval-approve"){
  if(!confirm(`Activate copy trading for subscriber ${id}?`))return;
  endpoint=`/onboarding/${id}/approval`;payload={decision:"APPROVED"};
 }else if(action==="approval-reject"){
  const reason=prompt("Reason for rejecting activation:");if(!reason)return;
  endpoint=`/onboarding/${id}/approval`;payload={decision:"REJECTED",reason};
 }else if(action==="copier-code"){
  const account=onboarding.broker_account,accountId=button.dataset.accountId;
  if(!account||!accountId){setStatus("Verified MT5 account is required",true);return}
  const mode=String(account.server||"").toLowerCase().includes("demo")?"DEMO":"LIVE";
  const currency=String(account.currency||"USD").toUpperCase();
  const unit=["USC","USCENT","USCENTS","CENT"].includes(currency)||account.account_type==="CENT"?"USC":"USD";
  try{
   const data=await apiPost("/copyhub/v1/admin/receivers",{subscriber_id:id,broker_account_id:Number(accountId),environment:mode,currency_unit:unit,is_cent_account:unit==="USC"});
   if(navigator.clipboard)await navigator.clipboard.writeText(data.activation_code);
   window.prompt("Copy this one-time Bethel Copier activation code. It expires in 24 hours:",data.activation_code);
   setStatus("Copier activation code created");await loadCopyHub();
  }catch(error){setStatus(error.message||"Unable to create copier code",true)}
  return;
 }else if(action==="live-enable"){
  const accountId=button.dataset.accountId;
  if(!accountId){setStatus("Verified MT5 account is required",true);return}
  const confirmation=prompt("Live trading can create real gains and losses. Type ENABLE LIVE MT5 exactly:");
  if(confirmation!=="ENABLE LIVE MT5"){setStatus("Live activation cancelled",true);return}
  endpoint=`/broker-accounts/${accountId}/live-access`;payload={enabled:true,confirmation};
 }else if(action==="live-disable"){
  const accountId=button.dataset.accountId;
  if(!accountId)return;
  if(!confirm(`Stop live trading for subscriber ${id} immediately?`))return;
  endpoint=`/broker-accounts/${accountId}/live-access`;payload={enabled:false,confirmation:"DISABLE LIVE MT5"};
 }else{return}
 button.disabled=true;
 try{await apiPost(endpoint,payload);setStatus(action.startsWith("live-")?"Live-access control updated":"Subscriber review updated");await loadOverview()}
 catch(error){setStatus(typeof error.message==="string"?error.message:JSON.stringify(error.message),true);button.disabled=false}
}






async function loadOperations(){
 try{
  const [backups,events]=await Promise.all([apiGet("/admin/operations/backups"),apiGet("/admin/operations/security-events?limit=100")]);
  $("#backups-table").innerHTML=(backups.backups||[]).map(row=>`<tr>
   <td>${escapeHtml(row.created_at||"")}</td><td>${escapeHtml(row.filename||"")}</td>
   <td>${escapeHtml(row.reason||"")}</td><td>${Number(row.size_bytes||0).toLocaleString()} bytes</td>
   <td>${stateBadge(row.integrity_status)}</td><td><code>${escapeHtml((row.sha256||"").slice(0,18))}…</code></td>
  </tr>`).join("")||'<tr><td colspan="6">No backups recorded.</td></tr>';
  $("#security-events-table").innerHTML=(events.events||[]).map(row=>`<tr>
   <td>${escapeHtml(row.created_at||"")}</td><td>${stateBadge(row.severity)}</td>
   <td>${escapeHtml(row.event_type||"")}</td><td>${escapeHtml((row.method||"")+" "+(row.path||""))}</td>
   <td>${row.status_code??""}</td><td>${escapeHtml(row.ip_address||"")}</td><td>${escapeHtml(row.detail||"")}</td>
  </tr>`).join("")||'<tr><td colspan="7">No security events recorded.</td></tr>';
 }catch(error){$("#backups-table").innerHTML=`<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`}
}
$("#reload-operations").onclick=loadOperations;
$("#create-backup").onclick=async()=>{
 const button=$("#create-backup");button.disabled=true;
 try{await apiPost("/admin/operations/backups",{});await loadOperations()}
 catch(error){alert(error.message)}
 finally{button.disabled=false}
};

async function loadNotifications(){
 try{
  const data=await apiGet("/admin/notifications");
  $("#notification-config").textContent=data.smtp_configured?"SMTP is configured.":"SMTP configuration is required before emails can be delivered.";
  $("#notifications-table").innerHTML=(data.deliveries||[]).map(row=>`<tr>
   <td>${escapeHtml(row.created_at||"")}</td><td>${escapeHtml(row.recipient||"")}</td>
   <td>${escapeHtml(row.message_type||"")}</td><td>${escapeHtml(row.subject||"")}</td>
   <td>${stateBadge(row.status)}</td><td>${row.attempts??0}</td><td>${escapeHtml(row.error||"")}</td>
  </tr>`).join("")||'<tr><td colspan="7">No email deliveries recorded.</td></tr>';
 }catch(error){$("#notifications-table").innerHTML=`<tr><td colspan="7">${escapeHtml(error.message)}</td></tr>`}
}
$("#reload-notifications").onclick=loadNotifications;
$("#sync-notifications").onclick=async()=>{
 const button=$("#sync-notifications");button.disabled=true;
 try{await apiPost("/admin/notifications/synchronize",{});await loadNotifications()}
 catch(error){alert(error.message)}
 finally{button.disabled=false}
};

async function loadLegalAdmin(){
 try{
  const data=await apiGet("/admin/legal/acceptances");
  $("#legal-table").innerHTML=(data.subscribers||[]).map(row=>`<tr>
   <td><strong>${escapeHtml(row.subscriber_name||"Unknown")}</strong><br><small>ID ${row.subscriber_id} · ${escapeHtml(row.subscriber_email||"")}</small></td>
   <td>${row.accepted_count}</td><td>${row.required_count}</td>
   <td>${stateBadge(row.complete?"COMPLETE":"INCOMPLETE")}</td>
   <td>${(row.documents||[]).map(doc=>`${escapeHtml(doc.code)} ${escapeHtml(doc.version)} ${doc.accepted?"✓":"✗"}`).join("<br>")}</td>
  </tr>`).join("")||'<tr><td colspan="5">No subscribers found.</td></tr>';
 }catch(error){$("#legal-table").innerHTML=`<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`}
}
$("#reload-legal").onclick=loadLegalAdmin;

async function loadProfitShareAdmin(){
 try{
  const data=await apiGet("/admin/profit-share");
  const outstanding=Object.entries(data.outstanding_fees_by_currency||{}).map(([currency,total])=>paymentMoney(total,currency)).join(", ");
  $("#profit-share-outstanding").textContent=`Outstanding: ${outstanding||"None"}`;
  $("#profit-share-table").innerHTML=(data.accounts||[]).map(row=>`<tr>
   <td><strong>${escapeHtml(row.subscriber_name||"Unknown")}</strong><br><small>ID ${row.subscriber_id} · ${escapeHtml(row.subscriber_email||"")}</small></td>
   <td>${escapeHtml(paymentMoney(row.cumulative_net_profit,row.currency))}</td>
   <td>${escapeHtml(paymentMoney(row.high_water_mark,row.currency))}</td>
   <td>${escapeHtml(paymentMoney(row.eligible_profit,row.currency))}</td>
   <td><strong>${escapeHtml(paymentMoney(row.projected_fee,row.currency))}</strong></td>
   <td><button data-generate-profit-share="${row.subscriber_id}">Generate monthly statement</button></td>
  </tr>`).join("")||'<tr><td colspan="6">No subscribers have accepted the agreement.</td></tr>';
  $$("[data-generate-profit-share]").forEach(button=>button.onclick=async()=>{
   if(!confirm(`Generate the previous month statement for subscriber ${button.dataset.generateProfitShare}?`))return;
   button.disabled=true;
   try{await apiPost(`/admin/profit-share/${button.dataset.generateProfitShare}/generate`,{});setStatus("Profit-share statement generated");await loadProfitShareAdmin()}
   catch(error){setStatus(error.message,true);button.disabled=false}
  });
 }catch(error){$("#profit-share-table").innerHTML=`<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`}
}

async function loadSubscriptions(){
 try{
  const data=await apiGet("/admin/subscriptions"),counts=data.counts||{};
  $("#subscriptions-active").textContent=counts.ACTIVE||0;
  $("#subscriptions-grace").textContent=counts.GRACE||0;
  $("#subscriptions-expired").textContent=counts.EXPIRED||0;
  $("#subscriptions-suspended").textContent=counts.SUSPENDED||0;
  $("#subscriptions-table").innerHTML=(data.subscriptions||[]).map(row=>`<tr>
   <td><strong>${escapeHtml(row.subscriber_name||"Unknown")}</strong><br><small>ID ${row.subscriber_id} · ${escapeHtml(row.subscriber_email||"")}</small></td>
   <td>${stateBadge(row.status)}</td>
   <td>${escapeHtml(new Date(row.current_period_end).toLocaleString())}</td>
   <td>${escapeHtml(new Date(row.grace_until).toLocaleString())}</td>
   <td>${row.days_remaining}</td>
   <td><div class="subscription-actions">
    <button data-sub-action="renew" data-id="${row.subscriber_id}">Record renewal</button>
    <button data-sub-action="${row.manual_suspended?"resume":"suspend"}" data-id="${row.subscriber_id}">${row.manual_suspended?"Resume":"Suspend"}</button>
   </div></td>
  </tr>`).join("")||'<tr><td colspan="6">No paid subscriptions found.</td></tr>';
  $$("#subscriptions-table [data-sub-action]").forEach(button=>button.onclick=()=>handleSubscriptionAction(button));
 }catch(error){$("#subscriptions-table").innerHTML=`<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`}
}
async function handleSubscriptionAction(button){
 const id=button.dataset.id,action=button.dataset.subAction;
 let endpoint,payload;
 if(action==="renew"){
  const reference=prompt("Enter the verified renewal payment reference:");if(!reference)return;
  endpoint=`/admin/subscriptions/${id}/renew`;payload={reference};
 }else{
  if(!confirm(`${action==="suspend"?"Suspend":"Resume"} subscription for subscriber ${id}?`))return;
  endpoint=`/admin/subscriptions/${id}/suspension`;payload={suspended:action==="suspend"};
 }
 button.disabled=true;
 try{await apiPost(endpoint,payload);setStatus("Subscription updated");await Promise.all([loadSubscriptions(),loadOverview()])}
 catch(error){setStatus(error.message||"Subscription update failed",true);button.disabled=false}
}
$("#sweep-subscriptions").onclick=async()=>{
 try{await apiPost("/admin/subscriptions/sweep",{});setStatus("Subscription expiry check complete");await loadSubscriptions()}
 catch(error){setStatus(error.message,true)}
};

function paymentMoney(amount,currency){
 if(amount===null||amount===undefined)return "—";
 try{return new Intl.NumberFormat("en",{style:"currency",currency:currency||"USD"}).format(Number(amount))}
 catch{return `${Number(amount).toFixed(2)} ${currency||""}`}
}
async function loadPayments(){
 try{
  const data=await apiGet("/admin/payments");
  window.paymentRows=data.payments||[];
  $("#payment-total").textContent=data.total??0;
  $("#payment-pending").textContent=data.pending_review??0;
  $("#payment-paid").textContent=data.paid??0;
  $("#payment-rejected").textContent=data.rejected??0;
  const totals=Object.entries(data.paid_totals_by_currency||{});
  $("#payment-currency-totals").innerHTML=totals.map(([currency,total])=>`<span>${escapeHtml(currency)} paid: <strong>${paymentMoney(total,currency)}</strong></span>`).join("")||"<span>No paid totals yet.</span>";
  filterPayments();
 }catch(error){
  $("#payments-table").innerHTML=`<tr><td colspan="7">${escapeHtml(error.message)}</td></tr>`;
 }
}
function filterPayments(){
 const method=$("#payment-method-filter").value;
 const status=$("#payment-status-filter").value;
 const query=$("#payment-search").value.trim().toLowerCase();
 const rows=(window.paymentRows||[]).filter(row=>{
  if(method&&row.method!==method)return false;
  if(status&&row.status!==status)return false;
  return !query||`${row.subscriber_name} ${row.subscriber_email} ${row.reference} ${row.provider_transaction}`.toLowerCase().includes(query);
 });
 renderPayments(rows);
}
function renderPayments(rows){
 $("#payments-table").innerHTML=rows.map(row=>{
  let actions="Provider verified";
  if(row.admin_action&&row.method==="WISE")actions=`<div class="payment-actions"><button data-payment-action="approve-wise" data-payment-id="${row.payment_id}">Approve</button><button class="danger-button" data-payment-action="reject-wise" data-payment-id="${row.payment_id}">Reject</button></div>`;
  if(row.admin_action&&row.method==="MANUAL")actions=`<div class="payment-actions"><button data-payment-action="approve-manual" data-subscriber-id="${row.subscriber_id}">Approve</button><button class="danger-button" data-payment-action="reject-manual" data-subscriber-id="${row.subscriber_id}">Reject</button></div>`;
  return `<tr>
   <td>${escapeHtml(row.created_at?new Date(row.created_at).toLocaleString():"—")}</td>
   <td><strong>${escapeHtml(row.subscriber_name||"Unknown")}</strong><br><small>ID ${row.subscriber_id} · ${escapeHtml(row.subscriber_email||"")}</small></td>
   <td><span class="method-badge method-${row.method.toLowerCase()}">${escapeHtml(row.method)}</span></td>
   <td><span class="payment-reference">${escapeHtml(row.reference||"—")}</span><br><small>${escapeHtml(row.provider_transaction||"")}</small></td>
   <td>${escapeHtml(paymentMoney(row.amount,row.currency))}</td>
   <td>${stateBadge(row.status)}</td>
   <td>${actions}</td>
  </tr>`;
 }).join("")||'<tr><td colspan="7">No matching payment records.</td></tr>';
 $$("#payments-table [data-payment-action]").forEach(button=>button.onclick=()=>handlePaymentDecision(button));
}
async function handlePaymentDecision(button){
 const action=button.dataset.paymentAction;
 const approved=action.startsWith("approve-");
 const method=action.endsWith("-wise")?"WISE":"MANUAL";
 let reason=null;
 if(!approved){reason=prompt(`Reason for rejecting this ${method} payment:`);if(!reason)return}
 if(!confirm(`${approved?"Approve":"Reject"} this ${method} payment?`))return;
 const endpoint=method==="WISE"
  ?`/admin/payments/wise/${button.dataset.paymentId}/decision`
  :`/admin/payments/manual/${button.dataset.subscriberId}/decision`;
 button.disabled=true;
 try{
  await apiPost(endpoint,{decision:approved?"APPROVED":"REJECTED",reason});
  setStatus(`${method} payment ${approved?"approved":"rejected"}`);
  await Promise.all([loadPayments(),loadOverview()]);
 }catch(error){setStatus(error.message||"Payment decision failed",true);button.disabled=false}
}
$("#payment-method-filter").onchange=filterPayments;
$("#payment-status-filter").onchange=filterPayments;
$("#payment-search").oninput=filterPayments;
$("#reload-payments").onclick=loadPayments;

function renderPositions(rows){$("#positions-table").innerHTML=rows.map(r=>`<tr><td>${r.symbol||""}</td><td>${r.type||r.direction||""}</td><td>${r.volume??""}</td><td>${r.profit??""}</td></tr>`).join("")||'<tr><td colspan="4">No open positions.</td></tr>'}
function renderInvestors(rows){$("#investors-table").innerHTML=rows.map(r=>`<tr><td>${r.name||r.full_name||""}</td><td>${r.email||""}</td><td>${r.status||""}</td><td>${r.portfolio_value??r.current_value??"â€”"}</td><td><button type="button">View</button></td></tr>`).join("")||'<tr><td colspan="5">No investors found.</td></tr>'}
async function loadSettings(){try{const data=await apiGet("/admin/control/settings");fillForm($("#website-form"),data.website);fillForm($("#system-form"),data.system)}catch(e){setStatus(e.message,true)}}
$("#website-form").onsubmit=async e=>{e.preventDefault();try{await apiPut("/admin/control/settings/website",formData(e.currentTarget));setStatus("Website settings saved")}catch(err){setStatus(err.message,true)}}
$("#system-form").onsubmit=async e=>{e.preventDefault();try{await apiPut("/admin/control/settings/system",formData(e.currentTarget));setStatus("System settings saved")}catch(err){setStatus(err.message,true)}}
async function loadRoutes(){try{const data=await apiGet("/admin/control/routes");window.routeRows=data.routes||[];renderRoutes(window.routeRows)}catch(e){$("#routes-table").innerHTML=`<tr><td colspan="4">${e.message}</td></tr>`}}
function renderRoutes(rows){$("#routes-table").innerHTML=rows.map(r=>`<tr><td>${r.methods.join(", ")}</td><td>${r.path}</td><td>${r.name}</td><td>ONLINE</td></tr>`).join("")}
$("#route-search").oninput=e=>{const q=e.target.value.toLowerCase();renderRoutes((window.routeRows||[]).filter(r=>(r.path+" "+r.name+" "+r.methods.join(" ")).toLowerCase().includes(q)))}
$("#load-routes").onclick=loadRoutes;$("#refresh-button").onclick=()=>{loadOverview();loadSettings()};loadOverview();loadSettings();
setInterval(()=>{if($("#view-overview").classList.contains("active"))loadOverview()},60000);
