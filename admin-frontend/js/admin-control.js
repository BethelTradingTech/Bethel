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
      section.innerHTML=`<article class="panel unified-tool-panel"><div class="section-heading"><div><h2>${tool.title}</h2><p>Loading control…</p></div></div><div class="unified-tool-host" data-tool-host="${tool.id}"></div></article>`;
      main.appendChild(section);
      return section;
    }

    async function loadNativeTool(tool){
      const section=ensureView(tool);
      const host=section.querySelector(`[data-tool-host="${tool.id}"]`);
      if(!host||host.dataset.loaded==="true"||host.dataset.loading==="true")return;
      host.dataset.loading="true";
      host.innerHTML='<p class="notice">Loading control…</p>';
      try{
        const response=await fetch(tool.src,{credentials:"same-origin",cache:"no-store"});
        if(!response.ok)throw new Error(`Unable to load ${tool.title}`);
        const html=await response.text();
        const doc=new DOMParser().parseFromString(html,"text/html");
        host.replaceChildren(...[...doc.body.childNodes].map(node=>document.importNode(node,true)));
        doc.querySelectorAll("style").forEach(style=>{
          const copy=document.createElement("style");
          copy.dataset.unifiedToolStyle=tool.id;
          copy.textContent=style.textContent;
          document.head.appendChild(copy);
        });
        const scripts=[...doc.querySelectorAll("script")];
        for(const source of scripts){
          const script=document.createElement("script");
          [...source.attributes].forEach(attr=>script.setAttribute(attr.name,attr.value));
          if(source.src){
            script.src=new URL(source.getAttribute("src"),new URL(tool.src,location.origin)).href;
            await new Promise((resolve,reject)=>{script.onload=resolve;script.onerror=reject;document.body.appendChild(script)});
          }else{
            script.textContent=source.textContent;
            document.body.appendChild(script);
          }
        }
        host.dataset.loaded="true";
      }catch(error){
        host.innerHTML=`<p class="notice">${String(error.message||error)}</p><div class="review-actions"><button type="button" data-retry-tool="${tool.id}">Retry</button><button type="button" data-open-tool="${tool.id}">Open standalone control</button></div>`;
        host.querySelector(`[data-retry-tool="${tool.id}"]`)?.addEventListener("click",()=>{delete host.dataset.loading;loadNativeTool(tool)});
        host.querySelector(`[data-open-tool="${tool.id}"]`)?.addEventListener("click",()=>location.href=tool.src);
      }finally{delete host.dataset.loading}
    }

    function openTool(tool){
      document.querySelectorAll(".view").forEach(view=>view.classList.remove("active"));
      navButtons().forEach(button=>button.classList.toggle("active",button.dataset.toolView===tool.id));
      ensureView(tool).classList.add("active");
      const title=document.getElementById("page-title");
      if(title)title.textContent=tool.title;
      document.getElementById("sidebar")?.classList.remove("open");
      document.getElementById("overlay")?.classList.remove("show");
      loadNativeTool(tool);
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
        if(!button){button=document.createElement("button");button.type="button";button.textContent=tool.quick;quick.appendChild(button)}
        button.removeAttribute("onclick");button.removeAttribute("data-go");button.onclick=()=>openTool(tool);
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
      card=document.createElement("div");card.id="public-notice-management";card.className="wide";card.style.cssText="border:1px solid #36516b;background:#0d1726;border-radius:12px;padding:16px;margin-bottom:6px;display:grid;gap:12px";
      card.innerHTML=`<div><strong style="display:block;font-size:1.05rem;color:#e5eef9">Public Notice Disclosure</strong><small style="color:#94a3b8">Control the disclosure shown on the public website. You can enable or disable it and edit the text at any time.</small></div><label style="display:flex;align-items:center;gap:10px;color:#e5eef9"><input id="show-public-notice-disclosure" type="checkbox" style="width:18px;height:18px"> Enable Public Notice Disclosure on the public website</label><label>Disclosure text<textarea id="public-notice-text" name="public_notice_text" rows="7" placeholder="Enter the public disclosure text"></textarea></label><small id="public-notice-control-status" style="color:#94a3b8">This controls public presentation only. It does not change MT5, trading, KYC, payments, performance calculations, or onboarding.</small>`;grid.prepend(card);
    }
    const toggle=document.getElementById("show-public-notice-disclosure"),text=document.getElementById("public-notice-text"),status=document.getElementById("public-notice-control-status");
    async function loadPublicNoticeControl(){try{const data=await apiGet("/admin/control/settings");const website=data.website||{},controls=website.public_controls||{};toggle.checked=!!controls.show_public_notice_disclosure;text.value=website.public_notice_text||"";status.textContent=toggle.checked?"Public Notice Disclosure is currently ON.":"Public Notice Disclosure is currently OFF.";status.style.color=toggle.checked?"#34d399":"#94a3b8"}catch(error){status.textContent=error.message||"Unable to load Public Notice Disclosure settings";status.style.color="#f87171"}}
    toggle.addEventListener("change",()=>{status.textContent=toggle.checked?"Public Notice Disclosure will be enabled when you save.":"Public Notice Disclosure will be hidden when you save.";status.style.color=toggle.checked?"#34d399":"#fbbf24"});
    form.onsubmit=async event=>{event.preventDefault();const payload={};[...form.elements].forEach(el=>{if(!el.name||el.type==="submit"||el.id==="show-public-notice-disclosure")return;payload[el.name]=el.type==="checkbox"?el.checked:el.value});payload.public_controls={show_public_notice_disclosure:!!toggle.checked};try{const saveStatus=document.getElementById("save-status");if(saveStatus){saveStatus.textContent="Saving…";saveStatus.style.color="#10b981"}await apiPut("/admin/control/settings/website",payload);if(saveStatus){saveStatus.textContent="Website settings saved";setTimeout(()=>saveStatus.textContent="",5000)}status.textContent=toggle.checked?"Saved. Public Notice Disclosure is ON.":"Saved. Public Notice Disclosure is OFF.";status.style.color="#34d399"}catch(error){const saveStatus=document.getElementById("save-status");if(saveStatus){saveStatus.textContent=error.message||"Unable to save website settings";saveStatus.style.color="#ef4444"}status.textContent=error.message||"Unable to save Public Notice Disclosure settings";status.style.color="#f87171"}};
    await loadPublicNoticeControl();
  };
  core.onerror=()=>console.error("Bethel admin core failed to load");
  document.head.appendChild(core);
})();
