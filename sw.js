// Cratebox service worker: lets the installed app open with no connection.
// The app files are fetched fresh when online (so updates show up) and served from the cache offline.
const CACHE = "cratebox-0.10.2";
const CORE = ["./", "./cratebox.html", "./manifest.webmanifest", "./icon-180.png", "./icon-512.png", "./vendor/lame.min.js"];
const APP_FILE = /\/(cratebox\.html|index\.html|manifest\.webmanifest|icon-\d+\.png|vendor\/lame\.min\.js)?$/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin && APP_FILE.test(url.pathname)) {
    // offline, or GitHub Pages answering with an error page (it briefly 404s while it redeploys):
    // use the cached copy if there is one
    const cached = () => caches.match(req, { ignoreSearch: true }).then((m) => m || caches.match("./cratebox.html"));
    e.respondWith(
      fetch(req).then((r) => {
        if (r.ok) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return r; }
        return cached().then((m) => m || r);
      }).catch(cached)
    );
  } else if (/(^|\.)(gstatic|googleapis)\.com$/.test(url.hostname)) {
    // web fonts: cache first
    // (offline and not cached yet: answer with nothing, so the page just uses its fallback fonts)
    e.respondWith(caches.match(req).then((m) => m || fetch(req).then((r) => {
      const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return r;
    }).catch(() => new Response("", { status: 200, headers: { "Content-Type": req.destination === "style" ? "text/css" : "application/octet-stream" } }))));
  }
});
