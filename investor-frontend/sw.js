const CACHE_NAME = "bethel-investor-v8";
const APP_SHELL = [
    "./",
    "./login.html",
    "./offline.html",
    "./css/investor.css?v=3",
    "./js/auth.js?v=3",
    "./js/login.js?v=3",
    "./js/investor.js?v=3",
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
                .filter(key => key.startsWith("bethel-investor-") && key !== CACHE_NAME)
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
        requestUrl.pathname.startsWith("/investor/api/") ||
        requestUrl.pathname.startsWith("/investor/auth/")
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
