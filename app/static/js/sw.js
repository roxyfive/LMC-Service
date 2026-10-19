const CACHE = 'lmc-v5';
const SHELL = ['/', '/static/css/site.css', '/static/js/site.js', '/static/img/icon-192.png', '/static/img/logo-480.webp'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin || u.pathname.startsWith('/admin') || u.pathname.startsWith('/api')) return;
  if (r.mode === 'navigate') {
    e.respondWith(fetch(r).then(res => { const c = res.clone(); caches.open(CACHE).then(x => x.put(r, c)); return res; }).catch(() => caches.match(r).then(m => m || caches.match('/'))));
    return;
  }
  const heavy = u.pathname.endsWith('.mp4') || u.pathname.endsWith('.mp3');
  const fresh = u.pathname.endsWith('.css') || u.pathname.endsWith('.js');  // css/js: prima rete, poi cache offline
  const net = () => fetch(r).then(res => { if (res.ok && !heavy) { const c = res.clone(); caches.open(CACHE).then(x => x.put(r, c)); } return res; });
  e.respondWith(fresh ? net().catch(() => caches.match(r)) : caches.match(r).then(m => m || net()));
});
