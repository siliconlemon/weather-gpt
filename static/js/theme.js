(function (global) {
  "use strict";

  const STORAGE_KEY_THEME = "weather-gpt-theme";

  /** @type {() => Record<string, string>} */
  let getStrings = () => ({});

  function init(opts) {
    if (opts && typeof opts.getStrings === "function") getStrings = opts.getStrings;
  }

  function getStoredTheme() {
    try {
      return global.localStorage.getItem(STORAGE_KEY_THEME) === "light" ? "light" : "dark";
    } catch {
      return "dark";
    }
  }

  function getTheme() {
    return global.document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function themeToggleBtns() {
    return global.document.querySelectorAll("[data-theme-toggle]");
  }

  function refreshThemeToggleA11y() {
    const strings = getStrings();
    const light = getTheme() === "light";
    const labelKey = light ? "themeUseDark" : "themeUseLight";
    const fallback = light ? "Switch to dark theme" : "Switch to light theme";
    const ariaLabel = strings[labelKey] || fallback;
    const stateKey = light ? "themeNavUseLight" : "themeNavUseDark";
    const stateFallback = light ? "Light theme" : "Dark theme";
    themeToggleBtns().forEach((btn) => {
      btn.setAttribute("aria-pressed", light ? "true" : "false");
      btn.setAttribute("aria-label", ariaLabel);
      btn.setAttribute("title", ariaLabel);
      const labelSpan = btn.querySelector("[data-theme-toggle-label]");
      if (labelSpan) {
        labelSpan.textContent = strings[stateKey] || stateFallback;
      }
    });
  }

  function setTheme(theme) {
    const t = theme === "light" ? "light" : "dark";
    if (t === "light") global.document.documentElement.setAttribute("data-theme", "light");
    else global.document.documentElement.removeAttribute("data-theme");
    try {
      global.localStorage.setItem(STORAGE_KEY_THEME, t);
    } catch {
      /* ignore */
    }
    refreshThemeToggleA11y();
  }

  global.weatherGptTheme = {
    init,
    getStoredTheme,
    getTheme,
    setTheme,
    refreshThemeToggleA11y,
  };
})(typeof window !== "undefined" ? window : globalThis);
