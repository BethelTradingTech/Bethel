/*
Bethel Trading Technologies
Super Admin current-view refresh

This extension changes only the top Refresh button behavior. It does not bypass
API authentication. All API calls continue to use the existing authenticated
admin session token. The button no longer calls /admin/control/settings unless
settings are explicitly being edited/saved elsewhere.
*/
(function(){
    "use strict";

    const POLL_MS = 100;
    const MAX_WAIT_MS = 10000;

    function currentViewName(){
        const active = document.querySelector(".view.active");
        return active?.id?.replace(/^view-/, "") || "overview";
    }

    async function callIfAvailable(name){
        const fn = window[name];
        if(typeof fn === "function"){
            await fn();
            return true;
        }
        return false;
    }

    async function refreshActiveView(button){
        if(button){
            button.disabled = true;
            button.textContent = "Refreshing…";
        }

        try{
            const view = currentViewName();

            switch(view){
                case "overview":
                case "subscribers":
                case "investors":
                case "mt5":
                    await callIfAvailable("loadOverview");
                    break;
                case "operations":
                    await callIfAvailable("loadOperations");
                    break;
                case "notifications":
                    await callIfAvailable("loadNotifications");
                    break;
                case "legal":
                    await callIfAvailable("loadLegalAdmin");
                    break;
                case "profitshare":
                    await callIfAvailable("loadProfitShareAdmin");
                    break;
                case "subscriptions":
                    await callIfAvailable("loadSubscriptions");
                    break;
                case "payments":
                    await callIfAvailable("loadPayments");
                    break;
                case "copytrading":
                    await callIfAvailable("loadCopyHub");
                    break;
                case "analytics":
                    await callIfAvailable("loadAnalytics");
                    if(typeof window.refreshCompletePerformance === "function"){
                        await window.refreshCompletePerformance();
                    }
                    break;
                case "api":
                    await callIfAvailable("loadRoutes");
                    break;
                case "website":
                case "settings":
                    // Do not automatically request /admin/control/settings from
                    // the global Refresh button. Existing form values stay in
                    // place; explicit Save actions remain protected normally.
                    break;
                default:
                    await callIfAvailable("loadOverview");
            }

            if(typeof window.setStatus === "function"){
                window.setStatus("Refreshed");
            }
        }catch(error){
            if(typeof window.setStatus === "function"){
                window.setStatus(error?.message || "Refresh failed", true);
            }else{
                console.error("Bethel refresh failed", error);
            }
        }finally{
            if(button){
                button.disabled = false;
                button.textContent = "Refresh";
            }
        }
    }

    function install(){
        const started = Date.now();
        const timer = setInterval(()=>{
            const button = document.querySelector("#refresh-button");
            if(button && typeof window.loadOverview === "function"){
                clearInterval(timer);
                button.onclick = event => {
                    event.preventDefault();
                    refreshActiveView(button);
                };
                button.title = "Refresh the current section using your existing signed-in session";
                button.dataset.sessionRefresh = "true";
            }else if(Date.now() - started > MAX_WAIT_MS){
                clearInterval(timer);
                console.warn("Bethel current-view refresh could not attach.");
            }
        }, POLL_MS);
    }

    if(document.readyState === "loading"){
        document.addEventListener("DOMContentLoaded", install, {once:true});
    }else{
        install();
    }
})();
