/**
 * Banner gợi ý cài PWA (Chromium: beforeinstallprompt; iOS: hướng dẫn Thêm vào Màn hình chính).
 */
(function () {
  var STORAGE_KEY = 'gdp.pwaInstallDismissedUntil';
  var TTL_MS = 7 * 24 * 60 * 60 * 1000;

  function isStandalone() {
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      return true;
    }
    return window.navigator.standalone === true;
  }

  function dismissedUntil() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return 0;
      var t = parseInt(raw, 10);
      return isNaN(t) ? 0 : t;
    } catch (e) {
      return 0;
    }
  }

  function setDismissed() {
    try {
      localStorage.setItem(STORAGE_KEY, String(Date.now() + TTL_MS));
    } catch (e) {}
  }

  function isDismissed() {
    return Date.now() < dismissedUntil();
  }

  function isIosSafari() {
    var ua = window.navigator.userAgent || '';
    var iOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (!iOS) return false;
    var webkit = /WebKit/.test(ua);
    var noChrome = !/CriOS|FxiOS|EdgiOS/.test(ua);
    return webkit && noChrome;
  }

  function removeBanner() {
    var el = document.getElementById('gdp-pwa-install-banner');
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function whenBodyReady(fn) {
    if (document.body) fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function showBanner(opts) {
    if (document.getElementById('gdp-pwa-install-banner')) return;

    var wrap = document.createElement('div');
    wrap.id = 'gdp-pwa-install-banner';
    wrap.setAttribute('role', 'region');
    wrap.setAttribute('aria-label', 'Cài đặt ứng dụng');
    wrap.className =
      'fixed bottom-0 left-0 right-0 z-[200] flex flex-col gap-2 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between dark:border-slate-700 dark:bg-slate-900/95';

    var text = document.createElement('p');
    text.className = 'text-sm text-slate-700 dark:text-slate-200';
    text.textContent = opts.message;

    var actions = document.createElement('div');
    actions.className = 'flex flex-shrink-0 items-center gap-2';

    if (opts.primaryLabel && opts.onPrimary) {
      var btnInstall = document.createElement('button');
      btnInstall.type = 'button';
      btnInstall.className =
        'rounded-md bg-[#db0d29] px-3 py-2 text-sm font-medium text-white hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-[#db0d29]/40';
      btnInstall.textContent = opts.primaryLabel;
      btnInstall.addEventListener('click', function () {
        opts.onPrimary();
      });
      actions.appendChild(btnInstall);
    }

    var btnClose = document.createElement('button');
    btnClose.type = 'button';
    btnClose.className =
      'rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800';
    btnClose.textContent = 'Để sau';
    btnClose.addEventListener('click', function () {
      setDismissed();
      removeBanner();
    });
    actions.appendChild(btnClose);

    wrap.appendChild(text);
    wrap.appendChild(actions);
    document.body.appendChild(wrap);
  }

  if (isStandalone() || isDismissed()) return;

  var deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (document.getElementById('gdp-pwa-install-banner')) return;
    whenBodyReady(function () {
      if (document.getElementById('gdp-pwa-install-banner')) return;
      showBanner({
        message: 'Cài PluSor GDP+ lên màn hình chính để mở nhanh như ứng dụng.',
        primaryLabel: 'Cài đặt app',
        onPrimary: function () {
          if (!deferredPrompt) return;
          deferredPrompt.prompt();
          deferredPrompt.userChoice.finally(function () {
            deferredPrompt = null;
            removeBanner();
          });
        },
      });
    });
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    removeBanner();
  });

  if (isIosSafari() && !window.matchMedia('(display-mode: standalone)').matches) {
    window.addEventListener('load', function () {
      if (isStandalone() || isDismissed()) return;
      if (deferredPrompt) return;
      whenBodyReady(function () {
        if (document.getElementById('gdp-pwa-install-banner')) return;
        showBanner({
          message:
            'Trên iPhone/iPad: chạm nút Chia sẻ, chọn “Thêm vào Màn hình chính” để cài PluSor GDP+.',
          primaryLabel: null,
          onPrimary: null,
        });
      });
    });
  }
})();
