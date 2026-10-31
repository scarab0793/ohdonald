/* Remembers the visitor's language choice and sends returning Spanish readers to /es/. */
(() => {
  'use strict';
  const KEY = 'ohdonald-lang';
  let stored = null;
  try { stored = localStorage.getItem(KEY); } catch (_) { /* storage blocked: fine */ }

  document.querySelectorAll('.lang-nav a').forEach((a) => {
    a.addEventListener('click', () => {
      try { localStorage.setItem(KEY, a.hreflang); } catch (_) { /* ignore */ }
    });
  });

  const root = document.documentElement;
  if (root.dataset.home === 'true' && root.lang === 'en') {
    const wantsEs = stored === 'es' || (!stored && /^es\b/i.test(navigator.language || ''));
    if (wantsEs) location.replace('/es/' + location.hash);
  }
})();
