// service-worker.js
// Service Worker cho PluSor PWA
// - Caching App Shell (Offline support)
// - Web Push Notifications

// Đổi tên khi rebrand PluSor. Cleanup an toàn: handler 'activate' xoá mọi cache
// có tên khác CACHE_NAME, nên cache cũ 'giadungplus-v7' được dọn tự động.
// v2: /static/ (ảnh/font/svg) đổi cache-first vĩnh viễn → stale-while-revalidate
// (trả cache ngay nhưng luôn tải nền bản mới) — hết stale asset sau deploy.
const CACHE_NAME = 'plusor-v2';
const OFFLINE_URL = '/offline/';
const FALLBACK_ICON_URL = '/static/icon/favicon-512.svg';

// VAPID public key (không bí mật) — fallback khi SW tự re-subscribe lúc chưa nhận được
// context từ trang (pushsubscriptionchange có thể chạy khi không có tab nào mở).
// Phải khớp GP_PUSH_CONFIG.vapidPublicKey + settings/firebase/keypair.txt.
const VAPID_PUBLIC_KEY =
  'BMAinpH2KhQxtclH3XM3UJ_9e-NvlKTzY-WIszcXxCkll7ISLR3BEdWKmgBgkXvjjILJz5Uh375hHwRj3IvaIHU';
// Cache riêng để lưu context push (csrf + url + vapid) cho lần SW tự re-subscribe.
const PUSH_CTX_CACHE = 'gdp-push-ctx-v1';
const PUSH_CTX_URL = '/__gdp_push_ctx__';

// Tài nguyên tĩnh cần cache ngay khi cài đặt
const PRE_CACHE_ASSETS = [
  OFFLINE_URL,
  FALLBACK_ICON_URL,
  'https://cdn.tailwindcss.com'
];

// Cài đặt SW và cache tài nguyên
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      console.log('[SW] Pre-caching app shell');
      await Promise.all(
        PRE_CACHE_ASSETS.map(async (assetUrl) => {
          try {
            await cache.add(assetUrl);
          } catch (err) {
            // Bỏ qua từng asset lỗi để không làm fail toàn bộ install.
            console.warn('[SW] Pre-cache failed for:', assetUrl, err);
          }
        })
      );
    })
  );
  self.skipWaiting();
});

// Kích hoạt SW và dọn dẹp cache cũ
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

function isHttpOrHttps(url) {
  return url.protocol === 'http:' || url.protocol === 'https:';
}

function isLocalScriptOrStyle(url, request) {
  if (url.origin !== self.location.origin || !url.pathname.startsWith('/static/')) {
    return false;
  }

  return (
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'worker' ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css')
  );
}

function cacheFreshResponse(request, response) {
  if (!response || response.status !== 200) return response;

  const responseToCache = response.clone();
  caches.open(CACHE_NAME).then((cache) => {
    return cache.put(request, responseToCache).catch((err) => {
      console.warn('[SW] cache.put skipped:', request.url, err);
    });
  });

  return response;
}

// Xử lý fetch requests
self.addEventListener('fetch', (event) => {
  // Bỏ qua các request POST hoặc request không phải từ trang web
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  // Cache API không hỗ trợ chrome-extension:, chrome:, blob:, v.v.
  if (!isHttpOrHttps(url)) {
    return;
  }

  // API nội bộ: ưu tiên network (tránh cache JSON cũ; chat/sync cần dữ liệu mới)
  if (
    url.pathname.startsWith('/chat/api/') ||
    url.pathname.startsWith('/api/')
  ) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // JS/CSS local cần ưu tiên bản mới để tránh stale asset sau deploy.
  if (isLocalScriptOrStyle(url, event.request)) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => cacheFreshResponse(event.request, networkResponse))
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Tài nguyên tĩnh còn lại (ảnh, font từ /static/ hoặc CDN):
  // STALE-WHILE-REVALIDATE — trả cache ngay cho nhanh, nhưng LUÔN tải nền bản
  // mới cập nhật vào cache. (Trước đây cache-first vĩnh viễn → asset stale mãi
  // sau deploy, phải F5 nhiều lần / đổi CACHE_NAME mới hết.)
  if (url.pathname.startsWith('/static/') || url.origin !== self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        const networkFetch = fetch(event.request)
          .then((networkResponse) => cacheFreshResponse(event.request, networkResponse))
          .catch(() => {
            // Fallback cho ảnh nếu offline
            if (event.request.destination === 'image') {
              return caches.match(FALLBACK_ICON_URL);
            }
          });
        return cachedResponse || networkFetch;
      })
    );
    return;
  }

  // Chiến lược cho HTML (Trang web): Network-First, fallback to Offline page
  event.respondWith(
    fetch(event.request)
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
          return caches.match(OFFLINE_URL);
        });
      })
  );
});

// ========================= WEB PUSH NOTIFICATIONS =========================

self.addEventListener('push', function (event) {
  let payload = {};
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload = { title: 'Thông báo', body: event.data.text() };
    }
  }

  const title = payload.title || 'Thông báo mới';
  const options = {
    body: payload.body || '',
    icon: payload.icon || FALLBACK_ICON_URL,
    badge: FALLBACK_ICON_URL,
    data: {
      url: payload.url || '/',
      payload: payload,
    },
    tag: payload.tag || 'general',
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  const data = (event.notification && event.notification.data) || {};
  const urlToOpen = data.url || '/';

  // Bóc room/message từ URL để báo tab đang mở mở đúng hội thoại + scroll tới tin
  // (không reload, không bắt user "đi tìm" trong chat chung).
  let room = null;
  let message = null;
  try {
    const u = new URL(urlToOpen, self.location.origin);
    room = u.searchParams.get('room');
    message = u.searchParams.get('message');
  } catch (e) {
    /* ignore */
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
      // Có tab đang mở → focus + báo chat.js mở đúng phòng/tin (SaaS: không rời trang).
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if ('focus' in client) {
          if (room) {
            try {
              client.postMessage({ type: 'GP_OPEN_CHAT', room: room, message: message, url: urlToOpen });
            } catch (e) {
              /* ignore */
            }
          }
          return client.focus();
        }
      }
      // Không có tab nào → mở mới tới URL có sẵn room+message (chat.js tự xử lý lúc load).
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen);
      }
    })
  );
});

// ===================== AUTO-HEAL SUBSCRIPTION =====================
// Web Push endpoint (đặc biệt Apple/Safari iOS + desktop) có thể hết hạn / xoay vòng.
// Khi đó push im lặng cho tới khi user tự bấm "Làm mới Push". Để tự lành:
//   1. Trang gửi context (csrf/url/vapid) cho SW qua postMessage → SW cache lại.
//   2. Trình duyệt fire `pushsubscriptionchange` → SW tự subscribe lại + POST /api/push/register/.

function swUrlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function savePushCtx(ctx) {
  try {
    const cache = await caches.open(PUSH_CTX_CACHE);
    await cache.put(
      PUSH_CTX_URL,
      new Response(JSON.stringify(ctx), { headers: { 'Content-Type': 'application/json' } })
    );
  } catch (e) {
    console.warn('[SW] savePushCtx failed', e);
  }
}

async function loadPushCtx() {
  try {
    const cache = await caches.open(PUSH_CTX_CACHE);
    const resp = await cache.match(PUSH_CTX_URL);
    if (resp) return await resp.json();
  } catch (e) {
    /* ignore */
  }
  return {};
}

async function resubscribeAndRegister() {
  const ctx = (await loadPushCtx()) || {};
  const vapid = ctx.vapidPublicKey || VAPID_PUBLIC_KEY;
  const apiUrl = ctx.apiRegisterUrl || '/api/push/register/';

  let sub = null;
  try {
    sub = await self.registration.pushManager.getSubscription();
  } catch (e) {
    sub = null;
  }
  if (!sub) {
    sub = await self.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: swUrlBase64ToUint8Array(vapid),
    });
  }

  const json = sub.toJSON();
  const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
  if (ctx.csrfToken) headers['X-CSRFToken'] = ctx.csrfToken;

  await fetch(apiUrl, {
    method: 'POST',
    headers: headers,
    credentials: 'include',
    body: JSON.stringify({
      device_type: ctx.deviceType || 'unknown',
      endpoint: json.endpoint,
      keys: json.keys || {},
    }),
  });
}

self.addEventListener('message', function (event) {
  const d = (event && event.data) || {};
  if (d.type === 'GP_PUSH_CTX') {
    event.waitUntil(
      savePushCtx({
        csrfToken: d.csrfToken || '',
        apiRegisterUrl: d.apiRegisterUrl || '/api/push/register/',
        vapidPublicKey: d.vapidPublicKey || VAPID_PUBLIC_KEY,
        deviceType: d.deviceType || 'unknown',
      })
    );
  }
});

self.addEventListener('pushsubscriptionchange', function (event) {
  event.waitUntil(
    resubscribeAndRegister().catch(function (err) {
      console.warn('[SW] pushsubscriptionchange re-subscribe failed', err);
    })
  );
});
