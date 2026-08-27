(function(){
  "use strict";
  const core=document.createElement("script");
  core.src="js/admin-control-core.js?v=20260827-disclosure-control";
  core.onload=async()=>{
    const form=document.getElementById("website-form");
    if(!form)return;
    const grid=form.querySelector(".form-grid");
    if(!grid)return;

    let card=document.getElementById("public-notice-management");
    if(!card){
      card=document.createElement("div");
      card.id="public-notice-management";
      card.className="wide";
      card.style.cssText="border:1px solid #36516b;background:#0d1726;border-radius:12px;padding:16px;margin-bottom:6px;display:grid;gap:12px";
      card.innerHTML=`
        <div>
          <strong style="display:block;font-size:1.05rem;color:#e5eef9">Public Notice Disclosure</strong>
          <small style="color:#94a3b8">Control the disclosure shown on the public website. You can enable or disable it and edit the text at any time.</small>
        </div>
        <label style="display:flex;align-items:center;gap:10px;color:#e5eef9">
          <input id="show-public-notice-disclosure" type="checkbox" style="width:18px;height:18px">
          Enable Public Notice Disclosure on the public website
        </label>
        <label>Disclosure text<textarea id="public-notice-text" name="public_notice_text" rows="7" placeholder="Enter the public disclosure text"></textarea></label>
        <small id="public-notice-control-status" style="color:#94a3b8">This controls public presentation only. It does not change MT5, trading, KYC, payments, performance calculations, or onboarding.</small>`;
      grid.prepend(card);
    }

    const toggle=document.getElementById("show-public-notice-disclosure");
    const text=document.getElementById("public-notice-text");
    const status=document.getElementById("public-notice-control-status");

    async function loadPublicNoticeControl(){
      try{
        const data=await apiGet("/admin/control/settings");
        const website=data.website||{};
        const controls=website.public_controls||{};
        toggle.checked=!!controls.show_public_notice_disclosure;
        text.value=website.public_notice_text||"";
        status.textContent=toggle.checked?"Public Notice Disclosure is currently ON.":"Public Notice Disclosure is currently OFF.";
        status.style.color=toggle.checked?"#34d399":"#94a3b8";
      }catch(error){
        status.textContent=error.message||"Unable to load Public Notice Disclosure settings";
        status.style.color="#f87171";
      }
    }

    toggle.addEventListener("change",()=>{
      status.textContent=toggle.checked?"Public Notice Disclosure will be enabled when you save.":"Public Notice Disclosure will be hidden when you save.";
      status.style.color=toggle.checked?"#34d399":"#fbbf24";
    });

    form.onsubmit=async event=>{
      event.preventDefault();
      const payload={};
      [...form.elements].forEach(el=>{
        if(!el.name||el.type==="submit"||el.id==="show-public-notice-disclosure")return;
        payload[el.name]=el.type==="checkbox"?el.checked:el.value;
      });
      payload.public_controls={show_public_notice_disclosure:!!toggle.checked};
      try{
        const saveStatus=document.getElementById("save-status");
        if(saveStatus){saveStatus.textContent="Saving…";saveStatus.style.color="#10b981";}
        await apiPut("/admin/control/settings/website",payload);
        if(saveStatus){saveStatus.textContent="Website settings saved";setTimeout(()=>saveStatus.textContent="",5000);}
        status.textContent=toggle.checked?"Saved. Public Notice Disclosure is ON.":"Saved. Public Notice Disclosure is OFF.";
        status.style.color="#34d399";
      }catch(error){
        const saveStatus=document.getElementById("save-status");
        if(saveStatus){saveStatus.textContent=error.message||"Unable to save website settings";saveStatus.style.color="#ef4444";}
        status.textContent=error.message||"Unable to save Public Notice Disclosure settings";
        status.style.color="#f87171";
      }
    };

    await loadPublicNoticeControl();
  };
  core.onerror=()=>console.error("Bethel admin core failed to load");
  document.head.appendChild(core);
})();
