(function () {
  function lucideRefresh() {
    if (typeof lucide !== "undefined" && lucide.createIcons) lucide.createIcons();
  }

  const form = document.getElementById("composer");
  const navDrawer = document.getElementById("nav-menu-drawer");
  const navToggle = document.getElementById("nav-menu-toggle");
  const navClose = document.getElementById("nav-menu-close");
  const navBackdrop = navDrawer?.querySelector(".nav-menu-drawer__backdrop");
  const themeToggleBtns = () => document.querySelectorAll("[data-theme-toggle]");
  const navLocaleBtns = () => document.querySelectorAll(".nav-locale-btn");

  const T = globalThis.weatherGptTheme;
  const L = globalThis.weatherGptLocale;
  const C = globalThis.weatherGptChat;

  T.init({ getStrings: () => L.getStrings() });
  L.init({
    localeTrigger: document.getElementById("locale-trigger"),
    localeMenu: document.getElementById("locale-menu"),
    localeCurrent: document.getElementById("locale-current"),
  });
  C.init({
    messagesEl: document.getElementById("messages"),
    chatClearBtn: document.getElementById("chat-clear"),
    suggestionsEl: document.getElementById("suggestions"),
    input: document.getElementById("input"),
    form,
    sendBtn: document.getElementById("send"),
    getStrings: () => L.getStrings(),
    getLocale: () => L.getLocale(),
    onLucide: lucideRefresh,
  });

  function onNavEscape(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeNavMenu();
    }
  }

  function closeNavMenu() {
    if (!navDrawer || !navToggle) return;
    navDrawer.hidden = true;
    navToggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("nav-menu-open");
    document.removeEventListener("keydown", onNavEscape);
    navToggle.focus();
  }

  function openNavMenu() {
    if (!navDrawer || !navToggle) return;
    L.closeLocaleMenu();
    navDrawer.hidden = false;
    navToggle.setAttribute("aria-expanded", "true");
    document.body.classList.add("nav-menu-open");
    document.addEventListener("keydown", onNavEscape);
    lucideRefresh();
    navClose?.focus();
  }

  themeToggleBtns().forEach((btn) => {
    btn.addEventListener("click", () => {
      T.setTheme(T.getTheme() === "light" ? "dark" : "light");
      lucideRefresh();
    });
  });

  navToggle?.addEventListener("click", () => {
    if (!navDrawer) return;
    if (navDrawer.hidden) openNavMenu();
    else closeNavMenu();
  });

  navClose?.addEventListener("click", () => closeNavMenu());
  navBackdrop?.addEventListener("click", () => closeNavMenu());

  navLocaleBtns().forEach((btn) => {
    btn.addEventListener("click", async () => {
      const v = btn.getAttribute("data-locale") === "en" ? "en" : "cs";
      const prev = L.getLocale();
      if (v === prev) return;
      L.setLocale(v);
      try {
        await L.loadI18n(v);
      } catch {
        /* ignore */
      }
      lucideRefresh();
    });
  });

  const desktopNavMq = window.matchMedia("(min-width: 641px)");
  function onDesktopNavMq(e) {
    if (e.matches) closeNavMenu();
  }
  if (typeof desktopNavMq.addEventListener === "function") {
    desktopNavMq.addEventListener("change", onDesktopNavMq);
  } else {
    desktopNavMq.addListener(onDesktopNavMq);
  }

  const localeTrigger = document.getElementById("locale-trigger");
  const localeMenu = document.getElementById("locale-menu");

  localeTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!localeMenu) return;
    if (localeMenu.hidden) L.openLocaleMenu();
    else L.closeLocaleMenu();
  });

  localeMenu?.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const item = document.activeElement?.closest?.(".locale-menu__item");
    if (!item) return;
    e.preventDefault();
    item.click();
  });

  localeMenu?.addEventListener("click", async (e) => {
    const item = e.target.closest(".locale-menu__item");
    if (!item) return;
    const v = item.getAttribute("data-value") === "en" ? "en" : "cs";
    const prev = L.getLocale();
    L.closeLocaleMenu();
    if (v === prev) return;
    L.setLocale(v);
    try {
      await L.loadI18n(v);
    } catch {
      /* ignore */
    }
    lucideRefresh();
  });

  T.setTheme(T.getStoredTheme());
  T.refreshThemeToggleA11y();

  const initial = L.getLocale();
  L.setLocale(initial);
  C.syncChatClearButton();
  C.syncSuggestionsStrip();
  L.loadI18n(initial)
    .then(() => {
      lucideRefresh();
      C.syncChatClearButton();
    })
    .catch(() => {
      lucideRefresh();
      C.syncChatClearButton();
      C.syncSuggestionsStrip();
    });
})();
