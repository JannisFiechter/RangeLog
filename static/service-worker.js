const CACHE_NAME = "rangelog-v1";
const ASSETS = [
  "/",
  "/start",
  "/exercises",
  "/stats",
  "/settings",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/training.js",
  "/static/js/exercise.js",
  "/static/js/stats.js",
  "/static/icons/icon.svg",
  "/static/icons/range-pattern.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) =>
      cached || fetch(event.request).catch(() => caches.match("/"))
    )
  );
});
