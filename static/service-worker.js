const CACHE_NAME = "rangelog-static-v2";
const STATIC_ASSETS = [
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/training.js",
  "/static/js/exercise.js",
  "/static/js/stats.js",
  "/static/icons/icon.svg",
  "/static/data/scoring.json"
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request));
    return;
  }

  if (url.origin === self.location.origin && url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) =>
        cached || fetch(event.request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
      )
    );
  }
});
