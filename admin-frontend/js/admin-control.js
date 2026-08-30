/*
Compatibility wrapper: the original Super Admin implementation is preserved in
admin-control-core.js and still owns these critical routes:
/admin/control/settings
/admin/operations/backups
/admin/notifications
/admin/legal/acceptances
/admin/subscriptions
/admin/payments
/connector/v1/admin/public-display
/broadcast/v1/admin/control
*/
(function(){
  "use strict";

  function installUnifiedAdminTools(){
    const main=document.querySelector("main.workspace");
    const nav=document.querySelector("#sidebar nav");
    if(!main||!nav)return;

    const tools=[
      {id:"website-control",title:"Website Control Center",label:"Website Control Center",icon:"◫",src:"/admin-frontend/website-management.html",after:"Website Management",quick:"Full website control"},
      {id:"promotions",title:"Pricing & Promotions",label:"Pricing & Promotions",icon:"💰",src:"/admin-frontend/promotions.html",existing:"Pricing & Promotions",quick:"Pricing & Promotions"},
      {id:"package-routing",title:"Package → Master Routing",label:"Package Routing",icon:"⇄",src:"/admin-frontend/package-routing.html",existing:"Package Routing",quick:"Manage Package Routing"},
      {id:"reviews",title:"Visitor Reviews",label:"Visitor Reviews",icon:"★",src:"/admin-frontend/reviews.html",after:"Notifications",quick:"Moderate visitor reviews"}
    ];

    function navButtons(){return [...nav.querySelectorAll(".nav-item")]}
    function buttonText(button){return (button.textContent||"").replace(/\s+/g," ").trim()}
    function findNav(label){return navButtons().find(button=>buttonText(button).includes(label))}

    function ensureView(tool){
      let section=document.getElementById(`view-${tool.id}`);
      if(section)return section;
      section=document.createElement("section");
      section.id=`view-${tool.id}`;
      section.className="view";
      section.innerHTML=`<article class="panel" style="padding:0;overflow:hidden;min-height:78vh"><iframe title="${tool.title}" src="${tool.src}" style="display:block;width:100%;height:78vh;min-height:720px;border:0;background:#07101f" loading="lazy" referrerpolicy="same-origin"></iframe></article>`;
      main.appendChild(section);
      return section;
    }

    function openTool(tool){
      document.querySelectorAll(".view").forEach(view=>view.classList.remove("active"));
      navButtons().forEach(button=>button.classList.toggle("active",button.dataset.toolView===tool.id));
      ensureView(tool).classList.add("active");
      const title=document.getElementById("page-title");
      if(title)title.textContent=tool.title;
      document.getElementById("sidebar")?.classList.remove("open");
      document.getElementById("overlay")?.classList.remove("show");
    }

    tools.forEach(tool=>{
      let button=tool.existing?findNav(tool.existing):null;
      if(!button){
        button=document.createElement("button");
        button.type="button";
        button.className="nav-item";
        button.innerHTML=`${tool.icon} <span>${tool.label}</span>`;
        const anchor=tool.after?findNav(tool.after):null;
        if(anchor&&anchor.nextSibling)nav.insertBefore(button,anchor.nextSibling);else nav.appendChild(button);
      }
      button.removeAttribute("onclick");
      button.removeAttribute("data-view");
      button.dataset.toolView=tool.id;
      button.onclick=()=>openTool(tool);
      ensureView(tool);
    });

    const quick=document.querySelector(".quick-grid");
    if(quick){
      tools.forEach(tool=>{
        let button=[...quick.querySelectorAll("button")].find(item=>buttonText(item).includes(tool.quick)||buttonText(item).includes(tool.label));
        if(!button){
          button=document.createElement("button");
          button.type="button";
          button.textContent=tool.quick;
          quick.appendChild(button);
        }
        button.removeAttribute("onclick");
        button.removeAttribute("data-go");
        button.onclick=()=>openTool(tool);
      });
    }
  }

  const core=document.createElement("script");
  core.src="js/admin-control-core.js?v=20260827-disclosure-control";
  core.onload=async()=>{
    installUnifiedAdminTools();

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
