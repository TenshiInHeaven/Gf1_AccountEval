/* GF Account Forge PWA service worker */
const CACHE = 'gf-account-forge-v7-20261125';
const SHELL = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './modules.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

async function coreList() {
  try {
    const response = await fetch('./data/core.json', { cache: 'no-store' });
    if (response.ok) {
      const list = await response.json();
      if (Array.isArray(list)) return list;
    }
  } catch (_error) { /* offline / first install */ }
  return [];
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const core = await coreList();
      const cache = await caches.open(CACHE);
      await cache.addAll([...new Set([...SHELL, ...core])]);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const network = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        const cache = await caches.open(CACHE);
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);
  return cached || network;
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('./index.html'))
    );
    return;
  }
  if (url.pathname.includes('/assets/avatars/')) {
    event.respondWith(cacheFirst(request));
    return;
  }
  if (url.pathname.endsWith('.json') || url.pathname.endsWith('.js') || url.pathname.endsWith('.css')) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
