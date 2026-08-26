(function () {
  "use strict";

  const API = "https://api.betheltradingtechnologies.com";
  const performanceSection = document.getElementById("performance");
  const broadcastSection = document.getElementById("public-broadcast");
  const liveSection = document.getElementById("public-live-mt5");
  if (!performanceSection) return;

  let loading = false;
  let publicWebsite = {};
  let publicControls = {};
  let publicSystem = {};

  const style = document.createElement("style");
  style.textContent = `
    #public-broadcast,#public-live-mt5{display:none!important;padding:0!important;margin:0!important;height:0!important;min-height:0!important;overflow:hidden!important}
    .public-admin-hidden{display:none!important}
    .unified-live-title{text-align:center;margin-bottom:1rem}.unified-live-title h2{font-size:2.25rem;margin-bottom:.5rem}.unified-live-title p{color:var(--text-secondary);max-width:760px;margin:0 auto}
    .unified-live-panel{background:var(--card-bg);border:2px solid rgba(16,185,129,.5);border-radius:18px;padding:1.25rem;display:grid;gap:1rem;box-shadow:0 0 28px rgba(16,185,129,.10)}
    .returns-panel{background:rgba(255,255,255,.018);border:1px solid var(--border-color);border-radius:12px;padding:1rem;overflow:hidden}.returns-panel h3{font-size:1rem;margin-bottom:.75rem;text-align:left}
    .track-table-wrap{width:100%;max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;-webkit-overflow-scrolling:touch}.track-table{width:100%;border-collapse:collapse;min-width:1050px;font-size:.8rem}.track-table th,.track-table td{padding:.55rem .6rem;border-bottom:1px solid var(--border-color);text-align:center;white-space:nowrap}.track-table th:first-child,.track-table td:first-child{text-align:left;font-weight:700}.track-table th:last-child,.track-table td:last-child{font-weight:800}
    .track-positive{color:#34d399}.track-negative{color:#fb7185}.track-neutral{color:var(--text-secondary)}.track-loading{color:var(--text-secondary);padding:1rem 0}.track-error{color:#fca5a5;padding:1rem 0}.track-history-label{color:var(--text-secondary);font-size:.78rem}
    .unified-live-panel .public-broadcast-shell,.unified-live-panel .live-mt5-shell{max-width:none;margin:0;width:100%}.unified-live-panel .public-broadcast-shell{border:1px solid rgba(16,185,129,.35);box-shadow:none}.unified-live-panel .live-mt5-shell{padding:1rem}#broadcast-slot[hidden],#telemetry-slot[hidden]{display:none!important}
    #admin-prelaunch-notice{max-width:980px;margin:-3.6rem auto 3rem;padding:1rem 1.2rem;border:1px solid rgba(245,158,11,.35);background:rgba(120,53,15,.16);border-radius:12px;color:#d1d5db;font-size:.82rem;line-height:1.55;text-align:left}#admin-prelaunch-notice strong{color:#fbbf24;margin-right:.35rem}
    #admin-site-closed{position:fixed;inset:0;z-index:99999;background:#0b0f19;color:#f3f4f6;display:flex;align-items:center;justify-content:center;padding:2rem;text-align:center}#admin-site-closed .box{max-width:680px;background:#111827;border:1px solid #243044;border-radius:18px;padding:2rem}#admin-site-closed h1{font-size:2rem;margin-bottom:1rem}#admin-site-closed p{color:#9ca3af}
    @media(max-width:600px){.unified-live-title h2{font-size:1.35rem}.unified-live-title p{font-size:.8rem}.unified-live-panel{padding:.6rem;border-width:1px}.returns-panel{padding:.6rem}.track-table{font-size:.72rem;min-width:900px}.track-table th,.track-table td{padding:.45rem .5rem}#admin-prelaunch-notice{margin:-2.4rem 1rem 2rem}}
  `;
  document.head.appendChild(style);

  const control = (key, fallback = true) => Object.prototype.hasOwnProperty.call(publicControls,key) ? !!publicControls[key] : fallback;
  const setVisible = (selector, visible) => document.querySelectorAll(selector).forEach(el => el.classList.toggle("public-admin-hidden", !visible));
  const setText = (selector, value) => { const el=document.querySelector(selector); if(el&&value!=null&&value!=="") el.textContent=String(value); };
  const fmtSignedPercent = (value, digits = 2) => { const n=Number(value); return Number.isFinite(n)?`${n>0?"+":""}${n.toFixed(digits)}%`:"—"; };
  const fmtDate = value => { if(!value)return "—"; const raw=String(value),d=new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw)?`${raw}T00:00:00Z`:raw); return Number.isNaN(d.getTime())?raw:d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"}); };

  function buildUnifiedDisplay(){
    const broadcastShell=broadcastSection?.querySelector(".public-broadcast-shell");
    const liveShell=liveSection?.querySelector(".live-mt5-shell");
    performanceSection.innerHTML=`<div class="unified-live-title"><h2>LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1</h2><p>Live read-only Bethel Terminal 1 broadcast and account telemetry, followed by the active master's monthly and yearly return record.</p></div><div id="unified-live-panel" class="unified-live-panel"><div id="broadcast-slot" hidden></div><div id="telemetry-slot" hidden></div><div class="returns-panel"><h3>Monthly & Yearly Returns</h3><div id="track-loading" class="track-loading">Loading return history…</div><div id="track-monthly" class="track-table-wrap" hidden></div></div></div>`;
    const broadcastSlot=document.getElementById("broadcast-slot"),telemetrySlot=document.getElementById("telemetry-slot");
    if(broadcastShell&&broadcastSlot)broadcastSlot.appendChild(broadcastShell);
    if(liveShell&&telemetrySlot)telemetrySlot.appendChild(liveShell);
    if(broadcastSection?.isConnected)broadcastSection.remove();
    if(liveSection?.isConnected)liveSection.remove();
  }

  function ensurePrelaunchNotice(){
    let notice=document.getElementById("admin-prelaunch-notice");
    if(!notice){notice=document.createElement("div");notice.id="admin-prelaunch-notice";const hero=document.querySelector(".hero");if(hero?.parentNode)hero.parentNode.insertBefore(notice,hero.nextSibling)}
    notice.replaceChildren();
    const strong=document.createElement("strong"),span=document.createElement("span");
    strong.textContent=publicWebsite.prelaunch_label||"PRE-LAUNCH NOTICE";span.textContent=publicWebsite.prelaunch_text||"";notice.append(strong,span);
    notice.classList.toggle("public-admin-hidden",!control("show_prelaunch_notice",true));
  }

  function renderSiteClosed(){
    const closed=!control("site_enabled",true)||!!publicSystem.maintenance_mode;let overlay=document.getElementById("admin-site-closed");
    if(!closed){overlay?.remove();return}
    if(!overlay){overlay=document.createElement("div");overlay.id="admin-site-closed";document.body.appendChild(overlay)}
    const title=document.createElement("h1"),p=document.createElement("p"),box=document.createElement("div");box.className="box";title.textContent=publicSystem.maintenance_mode?"Website maintenance":"Public website temporarily unavailable";p.textContent=publicWebsite.site_disabled_message||"Bethel Trading Technologies is updating its public information. Please check back shortly.";box.append(title,p);overlay.replaceChildren(box);
  }

  function applyPublicSettings(){
    renderSiteClosed();
    setVisible("header",control("show_navigation",true));setVisible(".hero",control("show_hero",true));setVisible("#about",control("show_about",true));setVisible("#services",control("show_services",true));setVisible("#visitor-reviews",control("show_reviews",true));setVisible("#contact",control("show_contact",true));setVisible("#contact .contact-form",control("show_contact_form",true));setVisible("#contact .social-networks-header,#contact .social-links-grid",control("show_social_links",true));setVisible("footer",control("show_footer",true));
    const registrationVisible=control("show_request_access",true)&&publicSystem.subscriber_registration_enabled!==false;setVisible(".onboarding-float,.nav-onboarding",registrationVisible);
    setText(".hero .badge",publicWebsite.hero_badge);setText(".hero h1",publicWebsite.hero_title);setText(".hero > p",publicWebsite.hero_description);
    const buttons=document.querySelectorAll(".hero .cta-group a");
    if(buttons[0]){buttons[0].classList.toggle("public-admin-hidden",!control("show_performance_cta",true));if(publicWebsite.primary_cta_text)buttons[0].textContent=publicWebsite.primary_cta_text;if(publicWebsite.primary_cta_url)buttons[0].href=publicWebsite.primary_cta_url}
    if(buttons[1]){buttons[1].classList.toggle("public-admin-hidden",!control("show_partner_cta",true));if(publicWebsite.secondary_cta_text)buttons[1].textContent=publicWebsite.secondary_cta_text;if(publicWebsite.secondary_cta_url)buttons[1].href=publicWebsite.secondary_cta_url}
    if(buttons[2]){buttons[2].classList.toggle("public-admin-hidden",!registrationVisible);if(publicWebsite.registration_cta_text)buttons[2].textContent=publicWebsite.registration_cta_text;if(publicWebsite.registration_cta_url)buttons[2].href=publicWebsite.registration_cta_url}
    document.querySelectorAll(".nav-onboarding,.onboarding-float").forEach(a=>{if(publicWebsite.registration_cta_text)a.textContent=publicWebsite.registration_cta_text;if(publicWebsite.registration_cta_url)a.href=publicWebsite.registration_cta_url});
    setText("#about .section-header h2",publicWebsite.about_title);setText("#about .section-header p",publicWebsite.about_subtitle);const about=document.querySelectorAll("#about .about-text p");if(about[0]&&publicWebsite.about_paragraph_1)about[0].textContent=publicWebsite.about_paragraph_1;if(about[1]&&publicWebsite.about_paragraph_2)about[1].textContent=publicWebsite.about_paragraph_2;
    setText("#services .section-header h2",publicWebsite.services_title);setText("#services .section-header p",publicWebsite.services_subtitle);document.querySelectorAll("#services .service-card").forEach((card,index)=>{const n=index+1,h=card.querySelector("h3"),p=card.querySelector("p");if(h&&publicWebsite[`service_${n}_title`])h.textContent=publicWebsite[`service_${n}_title`];if(p&&publicWebsite[`service_${n}_text`])p.textContent=publicWebsite[`service_${n}_text`]});
    setText("#contact .contact-info h3",publicWebsite.contact_title);setText("#contact .contact-info > p",publicWebsite.contact_description);const email=document.querySelector('#contact a[href^="mailto:"]');if(email&&publicWebsite.contact_email){email.textContent=publicWebsite.contact_email;email.href=`mailto:${publicWebsite.contact_email}`}
    const socialMap={"LinkedIn":publicWebsite.linkedin_url,"Facebook":publicWebsite.facebook_url,"Instagram":publicWebsite.instagram_url,"X (Twitter)":publicWebsite.x_url,"TikTok":publicWebsite.tiktok_url,"YouTube":publicWebsite.youtube_url,"WhatsApp Business":publicWebsite.whatsapp_url};document.querySelectorAll("#contact .social-item").forEach(a=>{const url=socialMap[a.title];if(url)a.href=url});
    const disclosure=document.querySelector("footer .disclaimer");if(disclosure&&publicWebsite.risk_disclosure)disclosure.textContent=publicWebsite.risk_disclosure;
    setText(".unified-live-title h2",publicWebsite.live_title);setText(".unified-live-title p",publicWebsite.live_description);setText(".returns-panel h3",publicWebsite.returns_title);ensurePrelaunchNotice();
    const anyPerformance=control("show_live_broadcast",true)||control("show_live_telemetry",true)||control("show_monthly_yearly_returns",true);performanceSection.classList.toggle("public-admin-hidden",!anyPerformance);document.querySelector(".returns-panel")?.classList.toggle("public-admin-hidden",!control("show_monthly_yearly_returns",true));
  }

  async function loadPublicSettings(){
    try{const response=await fetch(`${API}/admin/control/public-settings?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}});if(!response.ok)throw new Error();const data=await response.json();publicWebsite=data.website||{};publicControls=publicWebsite.public_controls||{};publicSystem=data.system||{};applyPublicSettings();await syncPublicVisibility()}catch(_){/* keep checked-in defaults if settings are temporarily unavailable */}
  }

  function renderMonthly(rows,historyStart,historyEnd){
    const container=document.getElementById("track-monthly");if(!container)return;const startPeriod=/^\d{4}-\d{2}/.test(String(historyStart||""))?String(historyStart).slice(0,7):null,endPeriod=/^\d{4}-\d{2}/.test(String(historyEnd||""))?String(historyEnd).slice(0,7):null;
    const valid=(Array.isArray(rows)?rows:[]).filter(r=>/^\d{4}-\d{2}$/.test(String(r.period||""))&&Number.isFinite(Number(r.return_percent))).filter(r=>(!startPeriod||r.period>=startPeriod)&&(!endPeriod||r.period<=endPeriod)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    if(!valid.length){container.innerHTML='<span class="track-history-label">Monthly return history is not yet available for the active master.</span>';container.hidden=false;return}
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const years=[...new Set(valid.map(r=>String(r.period).slice(0,4)))].sort(),byMonth=new Map(valid.map(r=>[String(r.period),Number(r.return_percent)])),table=document.createElement("table");table.className="track-table";const thead=document.createElement("thead"),headerRow=document.createElement("tr");["Year", ...months, "Year"].forEach(label=>{const th=document.createElement("th");th.textContent=label;headerRow.appendChild(th)});thead.appendChild(headerRow);table.appendChild(thead);const tbody=document.createElement("tbody");
    years.forEach(year=>{const tr=document.createElement("tr"),yearCell=document.createElement("td");yearCell.textContent=year;tr.appendChild(yearCell);const yearValues=[];for(let month=1;month<=12;month+=1){const key=`${year}-${String(month).padStart(2,"0")}`,value=byMonth.get(key),td=document.createElement("td");if(Number.isFinite(value)){td.textContent=fmtSignedPercent(value);td.className=value>0?"track-positive":value<0?"track-negative":"track-neutral";yearValues.push(value/100)}else{td.textContent="—";td.className="track-neutral"}tr.appendChild(td)}const annual=yearValues.length?(yearValues.reduce((factor,r)=>factor*(1+r),1)-1)*100:NaN,total=document.createElement("td");total.textContent=Number.isFinite(annual)?fmtSignedPercent(annual):"—";total.className=annual>0?"track-positive":annual<0?"track-negative":"track-neutral";tr.appendChild(total);tbody.appendChild(tr)});table.appendChild(tbody);container.replaceChildren(table);const note=document.createElement("div");note.className="track-history-label";note.style.marginTop=".65rem";note.textContent=`Active-master returns · ${fmtDate(historyStart)} — ${fmtDate(historyEnd)}.`;container.appendChild(note);container.hidden=false;
  }

  async function fetchSummary(){const response=await fetch(`${API}/performance/public-summary?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}});if(!response.ok)throw new Error("summary unavailable");const data=await response.json();if(!data.available)throw new Error("return history unavailable");return data}

  async function syncPublicVisibility(){
    const broadcastSlot=document.getElementById("broadcast-slot"),telemetrySlot=document.getElementById("telemetry-slot");try{const [broadcastResponse,telemetryResponse]=await Promise.all([fetch(`${API}/broadcast/v1/public/status?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}}),fetch(`${API}/connector/v1/public/live?ts=${Date.now()}`,{cache:"no-store",headers:{Accept:"application/json"}})]),broadcast=broadcastResponse.ok?await broadcastResponse.json():null,telemetry=telemetryResponse.ok?await telemetryResponse.json():null;if(broadcastSlot)broadcastSlot.hidden=!(control("show_live_broadcast",true)&&broadcast&&broadcast.enabled&&broadcast.hls_url);if(telemetrySlot)telemetrySlot.hidden=!(control("show_live_telemetry",true)&&telemetry&&telemetry.enabled)}catch(_){if(broadcastSlot)broadcastSlot.hidden=true;if(telemetrySlot)telemetrySlot.hidden=true}
  }

  async function loadReturns(){
    if(!control("show_monthly_yearly_returns",true)||loading)return;loading=true;try{const data=await fetchSummary(),summaryAgain=await fetchSummary();if(summaryAgain.account_number !== data.account_number)throw new Error("active master changed during refresh");renderMonthly(data.monthly_returns||[],data.history_start,data.history_end);const loadingEl=document.getElementById("track-loading");if(loadingEl)loadingEl.hidden=true}catch(_){const loadingEl=document.getElementById("track-loading");if(loadingEl){loadingEl.className="track-error";loadingEl.hidden=false;loadingEl.textContent="Monthly and yearly returns are temporarily unavailable while the active master record is refreshing."}}finally{loading=false}
  }

  buildUnifiedDisplay();loadPublicSettings();syncPublicVisibility();loadReturns();setInterval(syncPublicVisibility,5000);setInterval(loadPublicSettings,10000);setInterval(loadReturns, 15000);
})();
