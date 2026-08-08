/* Bethel Super Admin website traffic analytics */
(function(){
  if(typeof isAuthenticated!=="function" || !isAuthenticated()) return;

  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));

  function ensureView(){
    if(document.getElementById("view-traffic")) return;

    const nav = document.querySelector(".sidebar nav");
    if(nav){
      const button = document.createElement("button");
      button.className = "nav-item";
      button.dataset.view = "traffic";
      button.innerHTML = "📊 <span>Traffic Analytics</span>";
      button.addEventListener("click", () => {
        if(typeof showView === "function") showView("traffic");
        const title = document.getElementById("page-title");
        if(title) title.textContent = "Traffic Analytics";
        loadTraffic();
      });
      const websiteButton = nav.querySelector('[data-view="website"]');
      if(websiteButton?.nextSibling) nav.insertBefore(button, websiteButton.nextSibling);
      else nav.appendChild(button);
    }

    const overviewQuick = document.querySelector('#view-overview .quick-grid');
    if(overviewQuick){
      const quick = document.createElement("button");
      quick.type = "button";
      quick.textContent = "Website traffic analytics";
      quick.addEventListener("click", () => {
        if(typeof showView === "function") showView("traffic");
        const title = document.getElementById("page-title");
        if(title) title.textContent = "Traffic Analytics";
        loadTraffic();
      });
      overviewQuick.prepend(quick);
    }

    const main = document.querySelector("main.workspace");
    if(!main) return;
    const section = document.createElement("section");
    section.id = "view-traffic";
    section.className = "view";
    section.innerHTML = `
      <div class="metric-grid">
        <article class="metric"><small>Page views</small><strong id="traffic-pageviews">—</strong></article>
        <article class="metric"><small>Unique visitors</small><strong id="traffic-unique">—</strong></article>
        <article class="metric"><small>Visitors today</small><strong id="traffic-today">—</strong></article>
        <article class="metric"><small>Online now</small><strong id="traffic-online">—</strong></article>
        <article class="metric"><small>Bot requests</small><strong id="traffic-bots">—</strong></article>
      </div>
      <article class="panel">
        <div class="section-heading">
          <div><h2>Website Traffic Analytics</h2><p>Private Super Admin view. Raw visitor IP addresses are never stored.</p></div>
          <div>
            <select id="traffic-period" aria-label="Traffic period">
              <option value="1">Today</option><option value="7">7 days</option><option value="30" selected>30 days</option><option value="90">90 days</option>
            </select>
            <button id="traffic-refresh" type="button">Refresh</button>
          </div>
        </div>
        <div class="panel-grid">
          <article class="panel"><h3>Top Countries</h3><div id="traffic-countries"></div></article>
          <article class="panel"><h3>Top Cities</h3><div id="traffic-cities"></div></article>
          <article class="panel"><h3>Most Viewed Pages</h3><div id="traffic-pages"></div></article>
          <article class="panel"><h3>Traffic Sources</h3><div id="traffic-referrers"></div></article>
          <article class="panel"><h3>Devices</h3><div id="traffic-devices"></div></article>
          <article class="panel"><h3>Browsers</h3><div id="traffic-browsers"></div></article>
        </div>
        <h3>Recent Visitors</h3>
        <div class="table-wrap"><table><thead><tr><th>Page</th><th>Location</th><th>Device</th><th>Browser</th><th>Time</th></tr></thead><tbody id="traffic-recent"><tr><td colspan="5">No traffic recorded yet.</td></tr></tbody></table></div>
        <p id="traffic-privacy" class="notice">Raw visitor IP addresses are not stored; visitor identifiers are one-way hashed.</p>
      </article>`;
    main.appendChild(section);

    document.getElementById("traffic-refresh")?.addEventListener("click", loadTraffic);
    document.getElementById("traffic-period")?.addEventListener("change", loadTraffic);
  }

  function ranked(targetId, rows){
    const target = document.getElementById(targetId);
    if(!target) return;
    if(!rows?.length){ target.innerHTML = '<p class="muted">No traffic recorded yet.</p>'; return; }
    target.innerHTML = rows.map(row => `<div class="connector-details"><div><strong>${esc(row.name || "Unknown")}</strong><small>${Number(row.count || 0).toLocaleString()} views</small></div></div>`).join("");
  }

  async function loadTraffic(){
    ensureView();
    const period = Number(document.getElementById("traffic-period")?.value || 30);
    try{
      const response = await apiGet(`/traffic/admin/summary?days=${period}`);
      document.getElementById("traffic-pageviews").textContent = Number(response.total_page_views || 0).toLocaleString();
      document.getElementById("traffic-unique").textContent = Number(response.unique_visitors || 0).toLocaleString();
      document.getElementById("traffic-today").textContent = Number(response.visitors_today || 0).toLocaleString();
      document.getElementById("traffic-online").textContent = Number(response.online_now || 0).toLocaleString();
      document.getElementById("traffic-bots").textContent = Number(response.bot_requests || 0).toLocaleString();
      ranked("traffic-countries", response.countries);
      ranked("traffic-cities", response.cities);
      ranked("traffic-pages", response.top_pages);
      ranked("traffic-referrers", response.referrers);
      ranked("traffic-devices", response.devices);
      ranked("traffic-browsers", response.browsers);
      const recent = document.getElementById("traffic-recent");
      recent.innerHTML = (response.recent || []).map(row => `<tr><td>${esc(row.path)}</td><td>${esc([row.city,row.country].filter(Boolean).join(", ") || "Unavailable")}</td><td>${esc(row.device)}</td><td>${esc(row.browser)}</td><td>${row.time ? esc(new Date(row.time).toLocaleString()) : "—"}</td></tr>`).join("") || '<tr><td colspan="5">No traffic recorded yet.</td></tr>';
      document.getElementById("traffic-privacy").textContent = response.privacy || "Raw visitor IP addresses are not stored.";
    }catch(error){
      if(typeof setStatus === "function") setStatus(error.message || "Traffic analytics unavailable", true);
      const recent = document.getElementById("traffic-recent");
      if(recent) recent.innerHTML = `<tr><td colspan="5">${esc(error.message || "Traffic analytics unavailable")}</td></tr>`;
    }
  }

  window.loadBethelTrafficAnalytics = loadTraffic;
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", ensureView, {once:true});
  else ensureView();
})();
