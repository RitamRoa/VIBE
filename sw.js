const CACHE_NAME = 'vibe-news-v10';
const ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/manifest.json'
];

// Install
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

// Activate - Cleanup old caches
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
});

// Fetch - Stale-while-revalidate for API, Cache-first for assets
self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);

    // Navigations: Network first to avoid stale app shell issues
    if (e.request.mode === 'navigate') {
        e.respondWith(
            fetch(e.request)
                .then((response) => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put('/index.html', copy));
                    return response;
                })
                .catch(() => caches.match('/index.html'))
        );
        return;
    }

    // API calls: Network first, fall back to nothing (we handle offline in UI or use a different strategy)
    // Actually, for a news app, stick to Network First for data.
    if (url.pathname.startsWith('/news')) {
        e.respondWith(
            fetch(e.request).catch(() => {
                // Could return a cached fallback json here if we wanted to cache API responses in SW too
                return new Response(JSON.stringify({ articles: [] }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Static assets: Cache First
    e.respondWith(
        caches.match(e.request).then((response) => {
            return response || fetch(e.request);
        })
    );
});