(() => {
  if (window.GDPNavigationLayer) {
    return;
  }

  const CACHE_TTL_MS = 30000;
  const MAX_CACHE_ITEMS = 30;
  const PREFETCH_IDLE_MS = 1200;
  const SKELETON_DELAY_MS = 320;
  const APP_NAV_CONFIG = {
    ai_hub: { prefix: "/ai-hub/", enabled: true },
    products: { prefix: "/products/", enabled: true },
    kho: { prefix: "/kho/", enabled: true, excludedPrefixes: ["/kho/orders/sos_shopee/"] },
    cskh: { prefix: "/cskh/", enabled: false },
    settings: { prefix: "/settings/", enabled: true },
    marketing: { prefix: "/marketing/", enabled: true },
    knowledge: { prefix: "/knowledge/", enabled: true },
    quantri: {
      prefix: "/quantri/",
      enabled: true,
      excludedPrefixes: ["/quantri/api/", "/quantri/tasks/"],
    },
  };

  const prefetchCache = new Map();
  const loadedExternalScripts = new Set();
  const metrics = [];
  let inFlightController = null;
  let currentTargetUrl = null;
  let prefetchTimer = null;
  let skeletonDelayTimer = null;

  function now() {
    return performance.now();
  }

  function getPageContainer() {
    return document.getElementById("gdp-page-container");
  }

  function getPageContentRoot() {
    return document.getElementById("gdp-page-content");
  }

  function getNavProgressBar() {
    return document.getElementById("gdp-nav-progress");
  }

  function getNavSkeleton() {
    return document.getElementById("gdp-nav-skeleton");
  }

  function getCurrentNavApp() {
    const container = getPageContainer();
    const navApp = container && container.dataset ? container.dataset.navApp : "";
    if (navApp && APP_NAV_CONFIG[navApp]) {
      return navApp;
    }

    const pathname = window.location.pathname;
    for (const [appName, cfg] of Object.entries(APP_NAV_CONFIG)) {
      if (pathname.startsWith(cfg.prefix)) {
        return appName;
      }
    }
    return "";
  }

  function canHandleUrl(urlObj, navApp) {
    const appKey = navApp || getCurrentNavApp();
    const appConfig = APP_NAV_CONFIG[appKey];
    if (!appConfig || appConfig.enabled === false) return false;
    if (Array.isArray(appConfig.excludedPrefixes)) {
      for (const excludedPrefix of appConfig.excludedPrefixes) {
        if (urlObj.pathname.startsWith(excludedPrefix)) {
          return false;
        }
      }
    }

    return (
      urlObj.origin === window.location.origin &&
      urlObj.pathname.startsWith(appConfig.prefix) &&
      !urlObj.pathname.includes("/api/")
    );
  }

  function normalizeUrl(urlLike) {
    return new URL(urlLike, window.location.origin).toString();
  }

  function isModifiedClick(event) {
    return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
  }

  function findNavAnchor(target) {
    if (!target) return null;
    const anchor = target.closest("a[href]");
    if (!anchor) return null;

    const explicitScope = anchor.getAttribute("data-nav-link");
    if (explicitScope) {
      return anchor;
    }

    if (anchor.classList.contains("sidebar-link") && anchor.closest("#sidebar")) {
      return anchor;
    }

    if (anchor.closest(".quantri-soft-nav")) {
      return anchor;
    }

    return null;
  }

  function inlineScriptRequiresDomReady(contentRoot) {
    const scripts = Array.from(contentRoot.querySelectorAll("script:not([src])"));
    return scripts.some((script) => {
      const scriptType = (script.getAttribute("type") || "").trim().toLowerCase();
      if (scriptType && scriptType !== "text/javascript" && scriptType !== "application/javascript" && scriptType !== "module") {
        return false;
      }
      return /DOMContentLoaded|window\.onload|addEventListener\(\s*["']load["']/.test(script.textContent || "");
    });
  }

  function setProgressVisible(isVisible) {
    const bar = getNavProgressBar();
    if (!bar) return;
    if (isVisible) {
      bar.classList.remove("opacity-0");
      bar.classList.add("opacity-100");
      bar.style.width = "80%";
      return;
    }
    bar.style.width = "100%";
    setTimeout(() => {
      bar.classList.remove("opacity-100");
      bar.classList.add("opacity-0");
      bar.style.width = "0%";
    }, 140);
  }

  function setSkeletonVisible(isVisible) {
    const skeleton = getNavSkeleton();
    if (!skeleton) return;
    skeleton.classList.toggle("hidden", !isVisible);
  }

  function scheduleSkeletonShow() {
    clearTimeout(skeletonDelayTimer);
    skeletonDelayTimer = setTimeout(() => {
      setSkeletonVisible(true);
    }, SKELETON_DELAY_MS);
  }

  function cancelSkeletonShow() {
    clearTimeout(skeletonDelayTimer);
    setSkeletonVisible(false);
  }

  function emit(name, detail) {
    document.dispatchEvent(new CustomEvent(name, { detail }));
  }

  function registerMetric(entry) {
    metrics.push(entry);
    if (metrics.length > 120) metrics.shift();
    window.__GDP_NAV_METRICS = metrics;
  }

  function runCleanupHooks() {
    const cleanupFns = window.__gdpPageCleanupFns || [];
    while (cleanupFns.length) {
      const fn = cleanupFns.pop();
      try {
        fn();
      } catch (error) {
        console.warn("Cleanup hook failed:", error);
      }
    }
  }

  function ensureLifecycleApi() {
    if (window.GDPPageLifecycle) return;
    window.__gdpPageCleanupFns = window.__gdpPageCleanupFns || [];
    window.GDPPageLifecycle = {
      onCleanup(fn) {
        if (typeof fn === "function") {
          window.__gdpPageCleanupFns.push(fn);
        }
      },
    };
  }

  function parseHtmlDocument(htmlText) {
    const parser = new DOMParser();
    return parser.parseFromString(htmlText, "text/html");
  }

  function updateHistoryState(url, pageKey) {
    const state = { gdpEnhancedNav: true, pageKey: pageKey || "" };
    window.history.pushState(state, "", url);
  }

  function updateDocumentMeta(nextDocument, nextContainer) {
    if (nextDocument.title) {
      document.title = nextDocument.title;
    }
    const container = getPageContainer();
    if (!container || !nextContainer) return;
    if (nextContainer.dataset.pageKey) {
      container.dataset.pageKey = nextContainer.dataset.pageKey;
    }
    if (nextContainer.dataset.navApp) {
      container.dataset.navApp = nextContainer.dataset.navApp;
    }
  }

  function trimCache() {
    if (prefetchCache.size <= MAX_CACHE_ITEMS) return;
    const entries = Array.from(prefetchCache.entries()).sort((a, b) => a[1].ts - b[1].ts);
    while (entries.length > MAX_CACHE_ITEMS) {
      const oldest = entries.shift();
      if (oldest) prefetchCache.delete(oldest[0]);
    }
  }

  function getCached(url) {
    const item = prefetchCache.get(url);
    if (!item) return null;
    if (Date.now() - item.ts > CACHE_TTL_MS) {
      prefetchCache.delete(url);
      return null;
    }
    return item.html;
  }

  function setCached(url, html) {
    prefetchCache.set(url, { html, ts: Date.now() });
    trimCache();
  }

  function removeGdpNavStylesheetsFromHead() {
    document.querySelectorAll("link[data-gdp-nav-stylesheet]").forEach((el) => el.remove());
  }

  function promoteNavStylesheets(contentRoot) {
    if (!contentRoot) return;
    const links = Array.from(
      contentRoot.querySelectorAll('link[rel="stylesheet"][data-gdp-nav-stylesheet]'),
    );
    for (const link of links) {
      const href = link.getAttribute("href");
      if (!href) continue;
      const absoluteHref = normalizeUrl(href);
      const already = Array.from(document.head.querySelectorAll('link[rel="stylesheet"]')).some(
        (existing) => existing.getAttribute("href") && normalizeUrl(existing.getAttribute("href")) === absoluteHref,
      );
      if (!already) {
        document.head.appendChild(link.cloneNode(true));
      }
      link.remove();
    }
  }

  function scriptCacheKey(absoluteUrl, isModule) {
    return isModule ? `${absoluteUrl}#module` : absoluteUrl;
  }

  async function loadExternalScript(scriptUrl, options = {}) {
    const absoluteUrl = normalizeUrl(scriptUrl);
    const rerun = options.rerun === true;
    const isModule = options.module === true;
    const cacheKey = scriptCacheKey(absoluteUrl, isModule);
    if (!rerun && loadedExternalScripts.has(cacheKey)) {
      return;
    }

    // ES modules are deduped by URL in the module map; re-appending the same src after
    // soft-nav does not re-execute the module. Cache-bust so data-gdp-rerun actually runs.
    let loadUrl = absoluteUrl;
    if (rerun && isModule) {
      const busted = new URL(absoluteUrl, window.location.origin);
      busted.searchParams.set("_gdp_nav", String(Date.now()));
      loadUrl = busted.toString();
    }

    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = loadUrl;
      if (isModule) {
        script.type = "module";
      }
      script.async = false;
      script.onload = () => {
        if (!rerun) {
          loadedExternalScripts.add(cacheKey);
        }
        resolve();
      };
      script.onerror = () => reject(new Error(`Failed loading script: ${absoluteUrl}`));
      document.head.appendChild(script);
    });
  }

  async function executeScriptsInContainer(contentRoot) {
    if (!contentRoot) return;
    const scripts = Array.from(contentRoot.querySelectorAll("script"));

    for (const script of scripts) {
      const src = script.getAttribute("src");
      if (src) {
        const rerun = script.hasAttribute("data-gdp-rerun");
        const scriptType = (script.getAttribute("type") || "").trim().toLowerCase();
        const isModule = scriptType === "module";
        await loadExternalScript(src, { rerun, module: isModule });
        script.remove();
        continue;
      }

      const scriptType = (script.getAttribute("type") || "").trim().toLowerCase();
      const executableInlineTypes = new Set(["", "text/javascript", "application/javascript", "module"]);
      if (!executableInlineTypes.has(scriptType)) {
        // Keep data scripts (e.g. Django json_script type="application/json") untouched.
        continue;
      }

      const activeScript = document.createElement("script");
      for (const attr of script.attributes) {
        activeScript.setAttribute(attr.name, attr.value);
      }
      activeScript.textContent = script.textContent;
      script.replaceWith(activeScript);
    }
  }

  async function prefetch(urlLike) {
    const absoluteUrl = normalizeUrl(urlLike);
    if (getCached(absoluteUrl)) return;

    const urlObj = new URL(absoluteUrl);
    if (!canHandleUrl(urlObj, getCurrentNavApp())) return;

    try {
      const response = await fetch(absoluteUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-GDP-Prefetch": "1" },
      });
      if (!response.ok) return;
      const html = await response.text();
      setCached(absoluteUrl, html);
    } catch {
      // Prefetch best-effort only.
    }
  }

  function schedulePrefetch(urlLike) {
    clearTimeout(prefetchTimer);
    prefetchTimer = setTimeout(() => {
      prefetch(urlLike);
    }, PREFETCH_IDLE_MS);
  }

  function renderNavError(message, targetUrl) {
    const contentRoot = getPageContentRoot();
    if (!contentRoot) return;
    contentRoot.innerHTML = `
      <section class="p-4">
        <div class="bg-white border border-rose-200 rounded-2xl p-5">
          <h3 class="text-sm font-semibold text-rose-700">Không thể tải trang theo chế độ nhanh</h3>
          <p class="text-sm text-slate-600 mt-2">${message}</p>
          <div class="mt-4 flex items-center gap-2">
            <button id="gdp-nav-retry" class="px-3 py-2 text-sm bg-slate-900 text-white rounded-lg">Thử lại</button>
            <button id="gdp-nav-hard-reload" class="px-3 py-2 text-sm border rounded-lg">Tải lại toàn trang</button>
          </div>
        </div>
      </section>
    `;
    const retryBtn = document.getElementById("gdp-nav-retry");
    const hardReloadBtn = document.getElementById("gdp-nav-hard-reload");
    if (retryBtn) {
      retryBtn.addEventListener("click", () => navigateTo(targetUrl, { pushHistory: false }));
    }
    if (hardReloadBtn) {
      hardReloadBtn.addEventListener("click", () => {
        window.location.href = targetUrl;
      });
    }
  }

  async function navigateTo(urlLike, options = {}) {
    const absoluteUrl = normalizeUrl(urlLike);
    const pushHistory = options.pushHistory !== false;
    const start = now();

    if (inFlightController) {
      inFlightController.abort();
    }
    inFlightController = new AbortController();
    currentTargetUrl = absoluteUrl;

    emit("nav:start", { from: window.location.href, to: absoluteUrl });
    setProgressVisible(true);
    scheduleSkeletonShow();

    const cachedHtml = getCached(absoluteUrl);
    const usedCache = !!cachedHtml;

    try {
      const htmlText =
        cachedHtml ||
        (await fetch(absoluteUrl, {
          method: "GET",
          credentials: "same-origin",
          signal: inFlightController.signal,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        }).then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.text();
        }));

      if (!cachedHtml) {
        setCached(absoluteUrl, htmlText);
      }

      const parsed = parseHtmlDocument(htmlText);
      const nextContainer = parsed.querySelector("#gdp-page-container");
      const nextContentRoot = parsed.querySelector("#gdp-page-content");
      const currentContentRoot = getPageContentRoot();
      const currentNavApp = getCurrentNavApp();
      const nextNavApp = nextContainer && nextContainer.dataset ? nextContainer.dataset.navApp : "";

      if (!nextContainer || !nextContentRoot || !currentContentRoot || nextNavApp !== currentNavApp) {
        window.location.href = absoluteUrl;
        return;
      }

      // Safety-first for non-AI-Hub apps: if page scripts depend on DOMContentLoaded,
      // keep full reload to avoid silent behavior regressions.
      if (currentNavApp !== "ai_hub" && inlineScriptRequiresDomReady(nextContentRoot)) {
        window.location.href = absoluteUrl;
        return;
      }

      runCleanupHooks();
      emit("nav:swap", { to: absoluteUrl });

      removeGdpNavStylesheetsFromHead();
      currentContentRoot.innerHTML = nextContentRoot.innerHTML;
      promoteNavStylesheets(currentContentRoot);
      updateDocumentMeta(parsed, nextContainer);

      if (pushHistory) {
        updateHistoryState(absoluteUrl, nextContainer.dataset.pageKey || "");
      }

      await executeScriptsInContainer(currentContentRoot);

      if (window.GDPCoreUI && typeof window.GDPCoreUI.refreshActiveSidebarLinks === "function") {
        window.GDPCoreUI.refreshActiveSidebarLinks();
      }

      if (window.GDPCoreUI && typeof window.GDPCoreUI.checkRightPanel === "function") {
        window.GDPCoreUI.checkRightPanel();
      }

      emit("nav:done", { to: absoluteUrl, fromCache: usedCache });
      registerMetric({
        from: window.location.href,
        to: absoluteUrl,
        durationMs: Number((now() - start).toFixed(1)),
        fromCache: usedCache,
        ok: true,
      });
    } catch (error) {
      if (error && error.name === "AbortError") {
        return;
      }

      emit("nav:error", { to: absoluteUrl, message: String(error) });
      registerMetric({
        from: window.location.href,
        to: absoluteUrl,
        durationMs: Number((now() - start).toFixed(1)),
        fromCache: usedCache,
        ok: false,
      });
      renderNavError("Kết nối chưa ổn định hoặc dữ liệu trang không hợp lệ.", absoluteUrl);
    } finally {
      if (currentTargetUrl === absoluteUrl) {
        cancelSkeletonShow();
        setProgressVisible(false);
      }
    }
  }

  function handleClick(event) {
    if (isModifiedClick(event)) return;
    const anchor = findNavAnchor(event.target);
    if (!anchor) return;

    const href = anchor.getAttribute("href");
    if (!href || href.startsWith("#")) return;
    if (anchor.hasAttribute("download") || anchor.getAttribute("target") === "_blank") return;
    if (anchor.dataset.navMode === "full") return;

    const urlObj = new URL(href, window.location.origin);
    const currentNavApp = getCurrentNavApp();
    if (!canHandleUrl(urlObj, currentNavApp)) return;

    event.preventDefault();
    navigateTo(urlObj.toString(), { pushHistory: true });
  }

  function handleHoverPrefetch(event) {
    const anchor = findNavAnchor(event.target);
    if (!anchor) return;
    const href = anchor.getAttribute("href");
    if (!href) return;
    const urlObj = new URL(href, window.location.origin);
    const currentNavApp = getCurrentNavApp();
    if (!canHandleUrl(urlObj, currentNavApp)) return;
    schedulePrefetch(urlObj.toString());
  }

  function handlePopState() {
    const currentNavApp = getCurrentNavApp();
    if (!currentNavApp) return;
    const urlObj = new URL(window.location.href);
    if (!canHandleUrl(urlObj, currentNavApp)) {
      window.location.reload();
      return;
    }
    navigateTo(urlObj.toString(), { pushHistory: false });
  }

  function init() {
    ensureLifecycleApi();
    if (!getCurrentNavApp()) return;

    const contentRoot = getPageContentRoot();
    if (contentRoot) {
      promoteNavStylesheets(contentRoot);
    }

    document.querySelectorAll("script[src]").forEach((script) => {
      const src = script.getAttribute("src");
      if (!src) return;
      const scriptType = (script.getAttribute("type") || "").trim().toLowerCase();
      const isModule = scriptType === "module";
      loadedExternalScripts.add(scriptCacheKey(normalizeUrl(src), isModule));
    });

    document.addEventListener("click", handleClick, true);
    document.addEventListener("mouseover", handleHoverPrefetch, true);
    document.addEventListener("focusin", handleHoverPrefetch, true);
    window.addEventListener("popstate", handlePopState);
  }

  window.GDPNavigationLayer = {
    init,
    prefetch,
    navigateTo,
    metrics,
  };

  function bootNavigationLayer() {
    init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootNavigationLayer);
  } else {
    bootNavigationLayer();
  }
})();
