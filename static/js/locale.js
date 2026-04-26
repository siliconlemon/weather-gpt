(function (global) {
  "use strict";

  const STORAGE_KEY = "weather-gpt-locale";

  let strings = {};
  /** @type {HTMLElement | null} */
  let localeTrigger = null;
  /** @type {HTMLElement | null} */
  let localeMenu = null;
  /** @type {HTMLElement | null} */
  let localeCurrent = null;

  const navLocaleBtns = () => global.document.querySelectorAll(".nav-locale-btn");

  function init(opts) {
    if (!opts) return;
    localeTrigger = opts.localeTrigger || null;
    localeMenu = opts.localeMenu || null;
    localeCurrent = opts.localeCurrent || null;
  }

  function getStrings() {
    return strings;
  }

  function getLocale() {
    const v = global.localStorage.getItem(STORAGE_KEY) || "cs";
    return v === "en" ? "en" : "cs";
  }

  function setLocale(loc) {
    const normalized = loc === "en" ? "en" : "cs";
    global.localStorage.setItem(STORAGE_KEY, normalized);
    global.document.documentElement.lang = normalized;
    if (localeCurrent) {
      localeCurrent.textContent = normalized === "en" ? "English" : "Čeština";
    }
    if (localeMenu) {
      localeMenu.querySelectorAll(".locale-menu__item").forEach((el) => {
        const v = el.getAttribute("data-value") === "en" ? "en" : "cs";
        el.setAttribute("aria-selected", v === normalized ? "true" : "false");
      });
    }
    navLocaleBtns().forEach((btn) => {
      const v = btn.getAttribute("data-locale") === "en" ? "en" : "cs";
      btn.setAttribute("aria-pressed", v === normalized ? "true" : "false");
    });
  }

  function onLocaleDocClick(e) {
    if (!e.target.closest(".locale-dropdown")) closeLocaleMenu();
  }

  function onLocaleEscape(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeLocaleMenu();
      localeTrigger?.focus();
    }
  }

  function closeLocaleMenu() {
    if (!localeMenu || !localeTrigger) return;
    localeMenu.hidden = true;
    localeTrigger.setAttribute("aria-expanded", "false");
    global.document.removeEventListener("click", onLocaleDocClick);
    global.document.removeEventListener("keydown", onLocaleEscape);
  }

  function openLocaleMenu() {
    if (!localeMenu || !localeTrigger) return;
    localeMenu.hidden = false;
    localeTrigger.setAttribute("aria-expanded", "true");
    setTimeout(() => global.document.addEventListener("click", onLocaleDocClick), 0);
    global.document.addEventListener("keydown", onLocaleEscape);
    const selected = localeMenu.querySelector('.locale-menu__item[aria-selected="true"]');
    (selected || localeMenu.querySelector(".locale-menu__item"))?.focus();
  }

  async function loadI18n(loc) {
    const res = await global.fetch(`/static/i18n/${loc}.json`);
    if (!res.ok) throw new Error("i18n");
    strings = await res.json();
    global.document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) el.textContent = strings[k];
    });
    global.document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const k = el.getAttribute("data-i18n-placeholder");
      if (strings[k]) el.setAttribute("placeholder", strings[k]);
    });
    global.document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
      const k = el.getAttribute("data-i18n-aria-label");
      if (strings[k]) el.setAttribute("aria-label", strings[k]);
    });
    global.document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const k = el.getAttribute("data-i18n-title");
      if (strings[k]) el.setAttribute("title", strings[k]);
    });
    global.document.title = strings.title || global.document.title;
    const desc = strings.metaDescription;
    if (desc) {
      global.document.querySelector('meta[name="description"]')?.setAttribute("content", desc);
      global.document
        .querySelector('meta[property="og:description"]')
        ?.setAttribute("content", desc);
      global.document
        .querySelector('meta[name="twitter:description"]')
        ?.setAttribute("content", desc);
    }
    const t = strings.title;
    if (t) {
      global.document.querySelector('meta[property="og:title"]')?.setAttribute("content", t);
      global.document.querySelector('meta[name="twitter:title"]')?.setAttribute("content", t);
    }
    global.weatherGptTheme?.refreshThemeToggleA11y?.();
    global.weatherGptChat?.syncSuggestionsStrip?.();
  }

  global.weatherGptLocale = {
    init,
    getStrings,
    getLocale,
    setLocale,
    loadI18n,
    closeLocaleMenu,
    openLocaleMenu,
  };
})(typeof window !== "undefined" ? window : globalThis);
