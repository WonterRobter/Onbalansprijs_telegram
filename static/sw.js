// Een simpele Service Worker om Chrome tevreden te stellen
self.addEventListener('install', (e) => {
  console.log('[Service Worker] Install');
});

self.addEventListener('fetch', (e) => {
  // Gewoon doorlaten, we cachen (nog) niets
  // Dit is nodig voor de PWA-installatie eis
});