const CACHE_NAME = 'medical-ai-v1';
const STATIC_ASSETS = [
    '/static/index.html',
    '/static/login.html',
    '/static/css/common.css',
    '/static/css/chat.css',
    '/static/js/common.js',
    '/static/js/chat.js'
];

// 安装时缓存静态资源
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// 激活时清理旧缓存
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// 拦截请求，优先从缓存读取
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // API 请求不走缓存
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // 静态资源优先缓存
    if (request.method === 'GET') {
        event.respondWith(
            caches.match(request).then((response) => {
                if (response) {
                    return response;
                }
                return fetch(request).then((fetchResponse) => {
                    if (fetchResponse.ok) {
                        const clone = fetchResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, clone);
                        });
                    }
                    return fetchResponse;
                });
            }).catch(() => {
                // 离线时返回缓存的 index.html
                if (request.mode === 'navigate') {
                    return caches.match('/static/index.html');
                }
            })
        );
    }
});
