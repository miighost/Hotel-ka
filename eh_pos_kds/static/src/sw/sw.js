/**
 * Best effort service worker for the kitchen board. It caches the shell assets
 * (the JS and CSS bundles, fonts and the brand mark) with a stale while
 * revalidate strategy, so the board can boot from cache during a brief server
 * outage. It is only registered on a secure origin; on a plain http kiosk it is
 * silently skipped, and the IndexedDB read cache covers offline there.
 */
const CACHE = "eh-kds-shell-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
    const req = event.request;
    if (req.method !== "GET") {
        return;
    }
    const url = req.url;
    const cacheable =
        url.includes("/web/assets/") ||
        url.includes("/eh_pos_kds_core/static/") ||
        url.includes("/eh_pos_kds/static/") ||
        url.includes("/web/static/fonts/");
    if (!cacheable) {
        return;
    }
    event.respondWith(
        caches.open(CACHE).then(async (cache) => {
            const hit = await cache.match(req);
            const network = fetch(req)
                .then((res) => {
                    if (res && res.ok) {
                        cache.put(req, res.clone());
                    }
                    return res;
                })
                .catch(() => null);
            return hit || (await network) || Response.error();
        })
    );
});
