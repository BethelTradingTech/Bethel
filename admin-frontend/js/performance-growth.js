/*
Bethel Trading Technologies
Super Admin Performance navigation

The legacy single-master Performance & Analytics screen has been retired from
navigation. Performance now opens the account-scoped multi-master dashboard.
This script deliberately does not fetch or render legacy performance endpoints,
which also prevents upstream HTML/502 responses from being injected into the
admin page.
*/
(function () {
  "use strict";

  const TARGET = "/admin-frontend/master-performance.html";

  function install() {
    const button = document.querySelector('[data-view="analytics"]');
    if (!button || button.dataset.masterPerformanceRedirect === "true") return;

    button.dataset.masterPerformanceRedirect = "true";
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      window.location.assign(TARGET);
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
