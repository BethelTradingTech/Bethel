const CACHE_NAME = "bethel-admin-v1";
const APP_SHELL = [
    "./",
    "./login.html",
    "./offline.html",
    "./css/admin.css",
    "./js/auth.js?v=20260725c",
    "./js/login.js?v=20260725c",
    "./icons/app-icon.svg"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys
                .filter(key => key.startsWith("bethel-admin-") && key !== CACHE_NAME)
                .map(key => caches.delete(key))
        ))
    );
    self.clients.claim();
});

self.addEventListener("fetch", event => {
    const requestUrl = new URL(event.request.url);

    if(
        event.request.method !== "GET" ||
        requestUrl.pathname.startsWith("/api/") ||
        requestUrl.pathname.startsWith("/auth/") ||
        requestUrl.pathname.startsWith("/admin/") ||
        requestUrl.pathname.startsWith("/mt5/") ||
        requestUrl.pathname.startsWith("/onboarding/")
    ){
        return;
    }

    if(event.request.mode === "navigate"){
        event.respondWith(
            fetch(event.request).catch(() => caches.match("./offline.html"))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => cached || fetch(event.request))
    );
});
