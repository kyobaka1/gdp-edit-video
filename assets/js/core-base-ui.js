(() => {
  if (window.GDPCoreUI) {
    return;
  }

  function refreshActiveSidebarLinks() {
    const currentPathname = window.location.pathname;
    const currentSearch = window.location.search;
    const links = document.querySelectorAll(".sidebar-link");

    const queryContainsAllParams = (current, expected) => {
      const currentParams = new URLSearchParams(current || "");
      const expectedParams = Array.from(new URLSearchParams(expected || "").entries()).filter(([, value]) => {
        return value !== "" && value !== null;
      });

      if (!expectedParams.length) return false;

      return expectedParams.every(([key, value]) => currentParams.getAll(key).includes(value));
    };

    const currentQueryModeLinks = Array.from(links).filter((link) => {
      const href = link.getAttribute("href");
      if (!href) return false;

      const url = new URL(href, window.location.origin);
      return url.pathname === currentPathname && url.search && queryContainsAllParams(currentSearch, url.search);
    });

    links.forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;

      link.classList.remove("bg-brandlight", "text-brand", "font-semibold");

      const url = new URL(href, window.location.origin);
      const linkPathname = url.pathname;
      const linkSearch = url.search;

      let isActive = false;

      if (linkPathname === currentPathname) {
        if (linkSearch) {
          isActive = queryContainsAllParams(currentSearch, linkSearch);
        } else {
          isActive = currentQueryModeLinks.length === 0;
        }
      }

      if (isActive) {
        link.classList.add("bg-brandlight", "text-brand", "font-semibold");

        const parent = link.closest("ul");
        if (parent) {
          parent.classList.remove("hidden");
          const button = parent.previousElementSibling;
          const arrow = button ? button.querySelector(".collapse-arrow") : null;
          if (arrow) arrow.classList.remove("-rotate-90");
        }
      }
    });
  }

  function checkRightPanel() {
    const rightPanelContainer = document.getElementById("rightPanelContainer");
    const placeholder = document.getElementById("rightPanelPlaceholder");

    if (!rightPanelContainer || !placeholder) return;

    const hasContent =
      Array.from(rightPanelContainer.children).some((child) => {
        return child.nodeType === 1 && child.offsetHeight > 0;
      }) ||
      (rightPanelContainer.textContent.trim().length > 0 &&
        rightPanelContainer.querySelector("div, span, p, button, form, input, select, textarea"));

    const is2KOrLarger = window.innerWidth >= 1920;

    if (hasContent) {
      placeholder.style.display = "none";
    } else if (is2KOrLarger) {
      placeholder.style.display = "block";
    } else {
      placeholder.style.display = "none";
    }
  }

  const SIDEBAR_ICON_PATHS = {
    activity:
      '<path d="M4 13h3l2-7 4 12 2-5h5"></path>',
    ads:
      '<path d="M4 17l6-6 4 4 6-7"></path><path d="M15 8h5v5"></path>',
    archive:
      '<path d="M4 7h16"></path><path d="M6 7v12h12V7"></path><path d="M9 11h6"></path><path d="M5 3h14l1 4H4z"></path>',
    assets:
      '<path d="M4 6h16v12H4z"></path><path d="M8 14l2.2-2.2L13 14.5l1.5-1.5L18 17"></path><circle cx="8.5" cy="9.5" r="1.2"></circle>',
    bank:
      '<path d="M4 10h16"></path><path d="M6 10v8"></path><path d="M10 10v8"></path><path d="M14 10v8"></path><path d="M18 10v8"></path><path d="M3 20h18"></path><path d="M12 4l8 4H4z"></path>',
    barcode:
      '<path d="M4 5v14"></path><path d="M8 5v14"></path><path d="M11 5v14"></path><path d="M16 5v14"></path><path d="M20 5v14"></path>',
    bot:
      '<rect x="5" y="7" width="14" height="11" rx="3"></rect><path d="M12 7V4"></path><circle cx="9.5" cy="12" r=".7"></circle><circle cx="14.5" cy="12" r=".7"></circle><path d="M9 15h6"></path>',
    box:
      '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"></path><path d="M12 12l8-4.5"></path><path d="M12 12v9"></path><path d="M12 12L4 7.5"></path>',
    briefcase:
      '<rect x="4" y="7" width="16" height="12" rx="2"></rect><path d="M9 7V5h6v2"></path><path d="M4 12h16"></path>',
    calendar:
      '<rect x="4" y="5" width="16" height="15" rx="2"></rect><path d="M8 3v4"></path><path d="M16 3v4"></path><path d="M4 10h16"></path>',
    card:
      '<rect x="4" y="6" width="16" height="12" rx="2"></rect><path d="M4 10h16"></path><path d="M8 15h3"></path>',
    cart:
      '<path d="M4 5h2l2 10h9l2-7H7"></path><circle cx="10" cy="19" r="1.5"></circle><circle cx="17" cy="19" r="1.5"></circle>',
    chart:
      '<path d="M5 19V9"></path><path d="M10 19V5"></path><path d="M15 19v-7"></path><path d="M20 19V3"></path>',
    check:
      '<path d="M5 12l4 4L19 6"></path>',
    clock:
      '<circle cx="12" cy="12" r="8"></circle><path d="M12 8v5l3 2"></path>',
    cog:
      '<path d="M12 8a4 4 0 100 8 4 4 0 000-8z"></path><path d="M4 12h2"></path><path d="M18 12h2"></path><path d="M12 4v2"></path><path d="M12 18v2"></path><path d="M6.3 6.3l1.4 1.4"></path><path d="M16.3 16.3l1.4 1.4"></path><path d="M17.7 6.3l-1.4 1.4"></path><path d="M7.7 16.3l-1.4 1.4"></path>',
    database:
      '<ellipse cx="12" cy="6" rx="7" ry="3"></ellipse><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"></path><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"></path>',
    dollar:
      '<circle cx="12" cy="12" r="8"></circle><path d="M12 7v10"></path><path d="M15 9.5c-.8-1-4-1.3-4 1 0 2.8 5 1.4 5 4 0 2.2-3.7 2-5 1"></path>',
    download:
      '<path d="M12 4v11"></path><path d="M7 10l5 5 5-5"></path><path d="M5 20h14"></path>',
    file:
      '<path d="M7 3h7l4 4v14H7z"></path><path d="M14 3v5h5"></path>',
    gift:
      '<path d="M4 10h16v10H4z"></path><path d="M12 10v10"></path><path d="M4 14h16"></path><path d="M8 10c-2-1.8-1.2-4 1-4 1.4 0 2.2 1.2 3 4"></path><path d="M16 10c2-1.8 1.2-4-1-4-1.4 0-2.2 1.2-3 4"></path>',
    home:
      '<path d="M4 11l8-7 8 7"></path><path d="M6 10v10h12V10"></path><path d="M10 20v-6h4v6"></path>',
    invoice:
      '<path d="M7 3h10v18l-2-1.2-2 1.2-2-1.2-2 1.2-2-1.2z"></path><path d="M9 8h6"></path><path d="M9 12h6"></path><path d="M9 16h4"></path>',
    key:
      '<circle cx="8" cy="12" r="3"></circle><path d="M11 12h9"></path><path d="M17 12v3"></path><path d="M14 12v2"></path>',
    list:
      '<path d="M8 6h12"></path><path d="M8 12h12"></path><path d="M8 18h12"></path><circle cx="4" cy="6" r="1"></circle><circle cx="4" cy="12" r="1"></circle><circle cx="4" cy="18" r="1"></circle>',
    lock:
      '<rect x="5" y="10" width="14" height="10" rx="2"></rect><path d="M8 10V7a4 4 0 018 0v3"></path>',
    message:
      '<path d="M5 6h14v10H9l-4 4z"></path><path d="M8 10h8"></path><path d="M8 13h5"></path>',
    packageCheck:
      '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"></path><path d="M12 12l8-4.5"></path><path d="M12 12v9"></path><path d="M8.5 13.5l2 2 4-4"></path>',
    palette:
      '<path d="M12 4a8 8 0 100 16h1.5a2 2 0 001.3-3.5 1.7 1.7 0 011.1-3H17a3 3 0 000-6h-.5A7.9 7.9 0 0012 4z"></path><circle cx="8.5" cy="10" r=".8"></circle><circle cx="11.5" cy="8" r=".8"></circle><circle cx="7.5" cy="13" r=".8"></circle>',
    people:
      '<path d="M16 19v-1.2c0-2-1.8-3.8-4-3.8H8c-2.2 0-4 1.8-4 3.8V19"></path><circle cx="10" cy="8" r="4"></circle><path d="M18 19v-1.5c0-1.8-1-3.3-2.5-4"></path><path d="M15 5.4a3.5 3.5 0 010 5.2"></path>',
    refresh:
      '<path d="M20 7v5h-5"></path><path d="M4 17v-5h5"></path><path d="M6 9a7 7 0 0111.5-2"></path><path d="M18 15a7 7 0 01-11.5 2"></path>',
    return:
      '<path d="M9 7H5v4"></path><path d="M5 11c2-4 9-5 13 0 3 4 0 9-5 9H8"></path>',
    search:
      '<circle cx="10.5" cy="10.5" r="5.5"></circle><path d="M15 15l5 5"></path>',
    shield:
      '<path d="M12 3l7 3v5c0 4.5-2.7 8-7 10-4.3-2-7-5.5-7-10V6z"></path><path d="M9 12l2 2 4-4"></path>',
    shop:
      '<path d="M5 10h14l-1-5H6z"></path><path d="M6 10v10h12V10"></path><path d="M9 20v-5h6v5"></path>',
    sparkles:
      '<path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z"></path><path d="M5 15l.8 2.2L8 18l-2.2.8L5 21l-.8-2.2L2 18l2.2-.8z"></path><path d="M19 14l.6 1.4L21 16l-1.4.6L19 18l-.6-1.4L17 16l1.4-.6z"></path>',
    tag:
      '<path d="M4 5v6l8 8 7-7-8-7z"></path><circle cx="9" cy="9" r="1.3"></circle>',
    ticket:
      '<path d="M4 8a2 2 0 012-2h12a2 2 0 012 2v3a2 2 0 000 4v3a2 2 0 01-2 2H6a2 2 0 01-2-2v-3a2 2 0 000-4z"></path><path d="M9 8v8"></path>',
    truck:
      '<path d="M3 7h11v9H3z"></path><path d="M14 10h3l4 4v2h-7z"></path><circle cx="7" cy="18" r="2"></circle><circle cx="17" cy="18" r="2"></circle>',
    upload:
      '<path d="M12 20V9"></path><path d="M7 14l5-5 5 5"></path><path d="M5 4h14"></path>',
    user:
      '<circle cx="12" cy="8" r="4"></circle><path d="M5 20c.8-4 4-6 7-6s6.2 2 7 6"></path>',
    video:
      '<rect x="4" y="7" width="11" height="10" rx="2"></rect><path d="M15 10l5-3v10l-5-3z"></path>',
  };

  const SIDEBAR_ICON_RULES = [
    [/dashboard|tổng quan|overview|home/i, "home"],
    [/product knowledge|tài liệu|training|knowledge/i, "file"],
    [/xnk|model/i, "briefcase"],
    [/inventory|tồn kho|snapshot|phân tích tồn/i, "chart"],
    [/pricing settings|price mgmt|pricing|price|giá/i, "dollar"],
    [/profit|cost|cogs|vốn|expenses|chi phí|cash|payment|finance|invoice|hóa đơn|tax|ledger|sổ giao dịch/i, "dollar"],
    [/supplier|nhà cung cấp/i, "briefcase"],
    [/container|template/i, "download"],
    [/purchase order|po\b|spo|import batches|nhập khẩu|customs|tờ khai/i, "archive"],
    [/variants|variant|sku/i, "packageCheck"],
    [/products|sản phẩm/i, "box"],
    [/ads|marketing|campaign|shopee ads|product ads/i, "ads"],
    [/brand|shop/i, "shop"],
    [/feedback|message|chat|reply|review/i, "message"],
    [/ticket|warranty|return|trả hàng|hoàn/i, "ticket"],
    [/order|đơn|picking|packing|gói|nhặt|ship|hỏa tốc|hoả tốc|express/i, "truck"],
    [/print|barcode|label|tem/i, "barcode"],
    [/copy images|image|ảnh/i, "assets"],
    [/video|get videos/i, "video"],
    [/extension|chrome|bot/i, "bot"],
    [/chấm công|bảng chấm công|duyệt công|attendance|report|báo cáo/i, "clock"],
    [/nhân sự|staff|profile|phòng ban|sơ đồ|permission|quyền/i, "people"],
    [/settings|config|cấu hình|sync|sapo|lark|push|notify|log|init|admin/i, "cog"],
  ];

  function sidebarIconSvg(iconName) {
    const paths = SIDEBAR_ICON_PATHS[iconName] || SIDEBAR_ICON_PATHS.list;
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" ' +
      'stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      paths +
      "</svg>"
    );
  }

  function pickSidebarIcon(link) {
    const text = (link.textContent || "").trim();
    const href = link.getAttribute("href") || "";
    const haystack = `${text} ${href}`;
    const match = SIDEBAR_ICON_RULES.find(([pattern]) => pattern.test(haystack));
    return match ? match[1] : "list";
  }

  function normalizeSidebarLinkContent(link) {
    if (link.dataset.gdpSidebarIcon === "1") return;
    link.dataset.gdpSidebarIcon = "1";

    const hasExplicitMigratedIcon = Boolean(
      link.dataset.khoSidebarLink ||
        link.dataset.productsSidebarLink ||
        link.dataset.cskhSidebarLink ||
        link.dataset.aiHubSidebarLink ||
        link.dataset.hcnsSidebarLink
    );
    let iconHost = link.querySelector(":scope > .gdp-sidebar-icon");
    if (!iconHost) {
      if (hasExplicitMigratedIcon) return;

      // Transitional fallback for non-migrated app sidebars only.
      iconHost = document.createElement("span");
      iconHost.className = "gdp-sidebar-icon";

      const existingSvg = link.querySelector("svg");
      if (existingSvg) {
        iconHost.appendChild(existingSvg);
      } else {
        iconHost.innerHTML = sidebarIconSvg(pickSidebarIcon(link));
      }
      link.insertBefore(iconHost, link.firstChild);
    }

    Array.from(link.children).forEach((child) => {
      if (child === iconHost) return;
      if (child.matches("span, strong, small")) {
        const text = (child.textContent || "").trim();
        const isMeta =
          child.className.indexOf("rounded-full") !== -1 ||
          child.className.indexOf("badge") !== -1 ||
          /^\d+([.,]\d+)?$/.test(text);
        child.classList.add(isMeta ? "gdp-sidebar-meta" : "gdp-sidebar-label");
      }
    });
  }

  function initSidebarIcons(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("#sidebar .sidebar-link").forEach(normalizeSidebarLinkContent);
  }

  const VI_DATE_TIME_SELECTOR = [
    'input[type="date"]',
    'input[type="datetime-local"]',
    'input[type="month"]',
    'input[type="week"]',
    'input[type="time"]',
  ].join(",");

  function ensureDateTimeLocaleStyles() {
    if (document.getElementById("gdp-date-time-locale-style")) return;

    const style = document.createElement("style");
    style.id = "gdp-date-time-locale-style";
    style.textContent = [
      ".gdp-date-time-localized{position:relative;color:transparent!important;-webkit-text-fill-color:transparent!important;}",
      ".gdp-date-time-localized::before{content:attr(data-gdp-display-value);position:absolute;left:.75rem;top:50%;transform:translateY(-50%);max-width:calc(100% - 2.5rem);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;pointer-events:none;color:rgb(var(--c-heading)/1);-webkit-text-fill-color:rgb(var(--c-heading)/1);}",
      ".gdp-date-time-localized:focus::before{color:rgb(var(--c-heading)/1);-webkit-text-fill-color:rgb(var(--c-heading)/1);}",
      ".gdp-date-time-localized::-webkit-calendar-picker-indicator{opacity:1;}",
    ].join("");
    document.head.appendChild(style);
  }

  function padDatePart(value) {
    return String(value || "").padStart(2, "0");
  }

  function formatDateTimeDisplayValue(input) {
    const value = input.value || "";
    if (!value) return "";

    if (input.type === "time") {
      return value.slice(0, 5);
    }

    if (input.type === "datetime-local") {
      const parts = value.split("T");
      const date = parts[0] || "";
      const time = (parts[1] || "").slice(0, 5);
      const displayDate = formatIsoDate(date);
      return [displayDate, time].filter(Boolean).join(" ");
    }

    if (input.type === "month") {
      const match = value.match(/^(\d{4})-(\d{2})$/);
      return match ? `${match[2]}/${match[1]}` : value;
    }

    return formatIsoDate(value);
  }

  function formatIsoDate(value) {
    const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) return value || "";
    return `${padDatePart(match[3])}/${padDatePart(match[2])}/${match[1]}`;
  }

  function syncDateTimeDisplay(input) {
    input.setAttribute("data-gdp-display-value", formatDateTimeDisplayValue(input));
  }

  function bindDateTimeLocaleInput(input) {
    if (input.dataset.gdpDateTimeLocaleBound === "1") {
      syncDateTimeDisplay(input);
      return;
    }

    input.dataset.gdpDateTimeLocaleBound = "1";
    ["input", "change", "blur", "focus", "click"].forEach((eventName) => {
      input.addEventListener(eventName, () => syncDateTimeDisplay(input));
    });
    syncDateTimeDisplay(input);
  }

  function normalizeDateTimeLocale(root) {
    ensureDateTimeLocaleStyles();

    const scope = root && root.querySelectorAll ? root : document;
    document.documentElement.lang = "vi-VN";

    scope.querySelectorAll(VI_DATE_TIME_SELECTOR).forEach((input) => {
      input.lang = "vi-VN";
      input.setAttribute("data-gdp-date-format", "dd/mm/yyyy");
      input.setAttribute("data-gdp-time-format", "24h");
      input.classList.add("gdp-date-time-localized");
      bindDateTimeLocaleInput(input);
    });
  }

  let dateTimeLocaleObserver = null;

  function initDateTimeLocale() {
    normalizeDateTimeLocale();

    if (dateTimeLocaleObserver || !document.body) return;

    dateTimeLocaleObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType !== 1) return;

          if (node.matches && node.matches(VI_DATE_TIME_SELECTOR)) {
            node.lang = "vi-VN";
            node.setAttribute("data-gdp-date-format", "dd/mm/yyyy");
            node.setAttribute("data-gdp-time-format", "24h");
            node.classList.add("gdp-date-time-localized");
            bindDateTimeLocaleInput(node);
            return;
          }

          normalizeDateTimeLocale(node);
        });
      });
    });

    dateTimeLocaleObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  function initSidebarCollapses() {
    const toggles = document.querySelectorAll(".collapse-toggle");
    toggles.forEach((btn) => {
      if (btn.dataset.gdpBound === "1") return;
      btn.dataset.gdpBound = "1";

      const id = btn.getAttribute("data-collapse-id");
      const body = document.getElementById(id);
      const arrow = btn.querySelector(".collapse-arrow");
      if (!body) return;

      btn.addEventListener("click", () => {
        const isHidden = body.classList.toggle("hidden");
        if (!arrow) return;
        if (isHidden) arrow.classList.add("-rotate-90");
        else arrow.classList.remove("-rotate-90");
      });
    });
  }

  function initDesktopSidebarToggle() {
    const btn = document.getElementById("gdp-sidebar-toggle");
    const sidebar = document.getElementById("sidebar");
    if (!btn || !sidebar) return;
    if (btn.dataset.gdpBound === "1") return;
    btn.dataset.gdpBound = "1";

    const STORAGE_KEY = "gdp_sidebar_hidden";
    const LEGACY_KEY = "quantri_base_sidebar_hidden";

    const ICON_OPEN =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="0.5" y="2" width="15" height="12" rx="1.5" ry="1.5" stroke="currentColor" stroke-width="1" fill="none"></rect><rect x="2" y="4" width="3.5" height="8" rx="0.5" fill="currentColor" opacity="1"></rect></svg>';
    const ICON_CLOSED =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="0.5" y="2" width="15" height="12" rx="1.5" ry="1.5" stroke="currentColor" stroke-width="1" fill="none"></rect><rect x="2" y="4" width="3.5" height="8" rx="0.5" fill="currentColor" opacity="0.4"></rect></svg>';

    function readStoredHidden() {
      try {
        const v = localStorage.getItem(STORAGE_KEY);
        if (v !== null) return v === "1";
        const legacy = localStorage.getItem(LEGACY_KEY);
        if (legacy !== null) {
          localStorage.setItem(STORAGE_KEY, legacy);
          return legacy === "1";
        }
      } catch (e) {}
      return false;
    }

    function persistHidden(hidden) {
      try {
        localStorage.setItem(STORAGE_KEY, hidden ? "1" : "0");
      } catch (e) {}
    }

    function setToggleIcon(sidebarHidden) {
      btn.innerHTML = sidebarHidden ? ICON_CLOSED : ICON_OPEN;
      btn.setAttribute("aria-pressed", sidebarHidden ? "false" : "true");
    }

    function applyForViewport(hidden) {
      const isMd = window.matchMedia("(min-width: 768px)").matches;
      if (isMd) {
        if (hidden) sidebar.classList.add("gdp-sidebar-hidden");
        else sidebar.classList.remove("gdp-sidebar-hidden");
        setToggleIcon(hidden);
      } else {
        sidebar.classList.remove("gdp-sidebar-hidden");
        setToggleIcon(false);
      }
    }

    function syncFromStorage() {
      applyForViewport(readStoredHidden());
    }

    syncFromStorage();

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!window.matchMedia("(min-width: 768px)").matches) return;
      const isHidden = sidebar.classList.contains("gdp-sidebar-hidden");
      const next = !isHidden;
      persistHidden(next);
      applyForViewport(next);
    });

    let resizeT = null;
    window.addEventListener("resize", () => {
      if (resizeT) clearTimeout(resizeT);
      resizeT = setTimeout(() => {
        resizeT = null;
        syncFromStorage();
      }, 100);
    });
  }

  function initMobileMenu() {
    const mobileMenuToggle = document.getElementById("mobileMenuToggle");
    const sidebarShell = document.getElementById("gdp-sidebar-shell");
    const sidebar = document.getElementById("sidebar");
    const mobileMenuOverlay = document.getElementById("mobileMenuOverlay");
    if (!mobileMenuToggle || !sidebarShell || !mobileMenuOverlay) return;
    if (mobileMenuToggle.dataset.gdpBound === "1") return;
    mobileMenuToggle.dataset.gdpBound = "1";

    let isMenuOpen = false;

    function closeDrawer() {
      sidebarShell.classList.add("-translate-x-full");
      mobileMenuOverlay.classList.add("hidden");
      isMenuOpen = false;
      document.body.style.overflow = "";
    }

    mobileMenuToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      sidebarShell.classList.toggle("-translate-x-full");
      mobileMenuOverlay.classList.toggle("hidden");
      isMenuOpen = !isMenuOpen;
      document.body.style.overflow = isMenuOpen ? "hidden" : "";
    });

    mobileMenuOverlay.addEventListener("click", closeDrawer);

    const navHost = sidebar || sidebarShell;
    navHost.addEventListener("click", (e) => {
      if (!e.target.closest("a")) return;
      setTimeout(() => {
        closeDrawer();
      }, 100);
    });
  }

  function initUserMenuDropdown() {
    const userMenuToggle = document.getElementById("userMenuToggle");
    const userMenuDropdown = document.getElementById("userMenuDropdown");
    if (!userMenuToggle || !userMenuDropdown) return;
    if (userMenuToggle.dataset.gdpBound === "1") return;
    userMenuToggle.dataset.gdpBound = "1";

    userMenuToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      userMenuDropdown.classList.toggle("hidden");
      const khoMenu = document.getElementById("khoDropdownMenu");
      if (khoMenu) khoMenu.classList.add("hidden");
    });

    document.addEventListener("click", (e) => {
      if (!userMenuToggle.contains(e.target) && !userMenuDropdown.contains(e.target)) {
        userMenuDropdown.classList.add("hidden");
      }
    });

    const menuLinks = userMenuDropdown.querySelectorAll("a, button");
    menuLinks.forEach((link) => {
      link.addEventListener("click", () => {
        if (link.tagName !== "BUTTON" || link.type !== "submit") {
          setTimeout(() => userMenuDropdown.classList.add("hidden"), 100);
        }
      });
    });
  }

  function initMobileBottomNav() {
    const nav = document.getElementById("bottom-navigation");
    const btn = document.getElementById("gdp-bottom-nav-toggle");
    const scroll = document.getElementById("gdp-bottom-nav-scroll");
    if (!nav || !btn || !scroll) return;
    if (btn.dataset.gdpBound === "1") return;
    btn.dataset.gdpBound = "1";

    const STORAGE_KEY = "gdp.mobileBottomNavCollapsed.v2";

    function readCollapsed() {
      try {
        return localStorage.getItem(STORAGE_KEY) === "1";
      } catch (e) {
        return false;
      }
    }

    function applyCollapsed(collapsed) {
      const root = document.documentElement;
      if (collapsed) root.classList.add("gdp-bottom-nav-collapsed");
      else root.classList.remove("gdp-bottom-nav-collapsed");
      try {
        localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
      } catch (e) {}
      try {
        scroll.inert = collapsed;
      } catch (e) {
        scroll.setAttribute("aria-hidden", collapsed ? "true" : "false");
      }
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }

    applyCollapsed(readCollapsed());

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const next = !document.documentElement.classList.contains("gdp-bottom-nav-collapsed");
      applyCollapsed(next);
    });
  }

  function initAppSwitcher() {
    const containers = document.querySelectorAll("[data-appswitch]");
    if (!containers.length) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Phải khớp HÌNH HỌC với core/templates/core/_app_switcher_item.html (h-7 / w-7 / gap-2 / pl-3 / pr-4).
    // Lệch một bên là item nhảy size khi soft-nav đổi app.
    // Chỉ dùng class CÓ trong gdp_tailwind_build.css — gap-1.5 / pl-2.5 / pr-3.5 không được biên dịch.
    const ACTIVE_CLASSES = ["is-active", "w-auto", "gap-2", "pl-3", "pr-4", "border-transparent", "bg-brand", "text-white"];
    const INACTIVE_CLASSES = ["w-7", "justify-center", "gap-0", "px-0", "border-line", "text-body", "hover:bg-raised", "hover:text-heading"];

    function setItemActive(el, isActive) {
      const label = el.querySelector(".gdp-appswitch-label");
      if (isActive) {
        el.classList.remove(...INACTIVE_CLASSES);
        el.classList.add(...ACTIVE_CLASSES);
        el.setAttribute("aria-current", "page");
        if (label) label.classList.remove("hidden");
      } else {
        el.classList.remove(...ACTIVE_CLASSES);
        el.classList.add(...INACTIVE_CLASSES);
        el.setAttribute("aria-current", "false");
        if (label) label.classList.add("hidden");
      }
    }

    // FLIP: đo vị trí/độ rộng cũ, đổi trạng thái (active nhảy lên đầu), rồi animate từ cũ về mới
    // để icon + tên "trượt" mượt lên đầu thay vì nhảy khựng.
    function animateReorder(container, clicked) {
      const items = Array.from(container.querySelectorAll("[data-appswitch-item]"));
      const firstRects = new Map(items.map((el) => [el, el.getBoundingClientRect()]));

      const current = container.querySelector(".is-active");
      if (current && current !== clicked) setItemActive(current, false);
      setItemActive(clicked, true);
      container.prepend(clicked);

      if (prefersReducedMotion) return;

      items.forEach((el) => {
        const first = firstRects.get(el);
        if (!first) return;
        const last = el.getBoundingClientRect();
        const dx = first.left - last.left;
        el.style.transition = "none";
        el.style.width = `${first.width}px`;
        el.style.transform = dx ? `translateX(${dx}px)` : "";
      });

      void container.offsetWidth;

      requestAnimationFrame(() => {
        items.forEach((el) => {
          el.style.transition =
            "width 300ms cubic-bezier(0.22,1,0.36,1), transform 300ms cubic-bezier(0.22,1,0.36,1), padding 300ms cubic-bezier(0.22,1,0.36,1), gap 300ms cubic-bezier(0.22,1,0.36,1), background-color 220ms ease, color 220ms ease";
          el.style.width = "";
          el.style.transform = "";
        });
      });

      setTimeout(() => {
        items.forEach((el) => {
          el.style.transition = "";
        });
      }, 360);
    }

    containers.forEach((container) => {
      if (container.dataset.gdpBound === "1") return;
      container.dataset.gdpBound = "1";
      container.addEventListener("click", (e) => {
        const clicked = e.target.closest("[data-appswitch-item]");
        if (!clicked || !container.contains(clicked)) return;
        if (clicked.classList.contains("is-active")) return;
        animateReorder(container, clicked);
      });
    });
  }

  function initPullToRefresh() {
    const ptrIndicator = document.getElementById("ptr-indicator");
    const scrollElement = document.querySelector("main");
    if (!ptrIndicator || !scrollElement) return;
    if (scrollElement.dataset.gdpPtrBound === "1") return;
    scrollElement.dataset.gdpPtrBound = "1";

    let touchStart = 0;
    let touchMove = 0;

    scrollElement.addEventListener(
      "touchstart",
      (e) => {
        if (scrollElement.scrollTop === 0) {
          touchStart = e.touches[0].pageY;
        }
      },
      { passive: true }
    );

    scrollElement.addEventListener(
      "touchmove",
      (e) => {
        if (scrollElement.scrollTop === 0 && touchStart > 0) {
          touchMove = e.touches[0].pageY - touchStart;
          if (touchMove > 0) {
            const pull = Math.min(touchMove / 2, 80);
            ptrIndicator.style.transform = `translateY(${pull - 64}px)`;
            if (touchMove > 120) {
              ptrIndicator.style.opacity = "1";
            }
          }
        }
      },
      { passive: true }
    );

    scrollElement.addEventListener("touchend", () => {
      if (touchMove > 150) {
        ptrIndicator.style.transform = "translateY(16px)";
        window.location.reload();
      } else {
        ptrIndicator.style.transform = "translateY(-100%)";
      }
      touchStart = 0;
      touchMove = 0;
    });
  }

  function initialize() {
    initDateTimeLocale();
    initSidebarIcons();
    initSidebarCollapses();
    initDesktopSidebarToggle();
    initMobileMenu();
    initMobileBottomNav();
    initAppSwitcher();
    initUserMenuDropdown();
    initPullToRefresh();
    refreshActiveSidebarLinks();
    checkRightPanel();
  }

  window.GDPCoreUI = {
    initialize,
    refreshActiveSidebarLinks,
    initSidebarIcons,
    checkRightPanel,
    normalizeDateTimeLocale,
  };

  document.addEventListener("DOMContentLoaded", initialize);
  window.addEventListener("resize", checkRightPanel);
  document.addEventListener("nav:done", () => {
    initSidebarIcons();
    normalizeDateTimeLocale();
    refreshActiveSidebarLinks();
    checkRightPanel();
  });
})();
