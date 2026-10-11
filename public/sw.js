// Service Worker for Garmin AI Coach Pro PWA
const CACHE_NAME = 'garmin-coach-v2';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Pass through non-GET and dynamic backend API requests
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  // Network-first with cache fallback for static assets
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
