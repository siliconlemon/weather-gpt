(function () {
  function lucideRefresh() {
    if (typeof lucide !== "undefined" && lucide.createIcons) lucide.createIcons();
  }

  const STORAGE_KEY = "weather-gpt-locale";
  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("composer");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const localeTrigger = document.getElementById("locale-trigger");
  const localeMenu = document.getElementById("locale-menu");
  const localeCurrent = document.getElementById("locale-current");

  let strings = {};
  const history = [];

  function getLocale() {
    const v = localStorage.getItem(STORAGE_KEY) || "cs";
    return v === "en" ? "en" : "cs";
  }

  function setLocale(loc) {
    const normalized = loc === "en" ? "en" : "cs";
    localStorage.setItem(STORAGE_KEY, normalized);
    document.documentElement.lang = normalized;
    if (localeCurrent) {
      localeCurrent.textContent = normalized === "en" ? "English" : "Čeština";
    }
    if (localeMenu) {
      localeMenu.querySelectorAll(".locale-menu__item").forEach((el) => {
        const v = el.getAttribute("data-value") === "en" ? "en" : "cs";
        el.setAttribute("aria-selected", v === normalized ? "true" : "false");
      });
    }
  }

  function closeLocaleMenu() {
    if (!localeMenu || !localeTrigger) return;
    localeMenu.hidden = true;
    localeTrigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", onLocaleDocClick);
    document.removeEventListener("keydown", onLocaleEscape);
  }

  function onLocaleDocClick(e) {
    if (!e.target.closest(".locale-dropdown")) closeLocaleMenu();
  }

  function onLocaleEscape(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeLocaleMenu();
      localeTrigger.focus();
    }
  }

  function openLocaleMenu() {
    if (!localeMenu || !localeTrigger) return;
    localeMenu.hidden = false;
    localeTrigger.setAttribute("aria-expanded", "true");
    setTimeout(() => document.addEventListener("click", onLocaleDocClick), 0);
    document.addEventListener("keydown", onLocaleEscape);
    const selected = localeMenu.querySelector('.locale-menu__item[aria-selected="true"]');
    (selected || localeMenu.querySelector(".locale-menu__item"))?.focus();
  }

  async function loadI18n(loc) {
    const res = await fetch(`/static/i18n/${loc}.json`);
    if (!res.ok) throw new Error("i18n");
    strings = await res.json();
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (strings[k]) el.textContent = strings[k];
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const k = el.getAttribute("data-i18n-placeholder");
      if (strings[k]) el.setAttribute("placeholder", strings[k]);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
      const k = el.getAttribute("data-i18n-aria-label");
      if (strings[k]) el.setAttribute("aria-label", strings[k]);
    });
    document.title = strings.title || document.title;
  }

  function messageIconName(role, extraClass) {
    if (extraClass && extraClass.includes("msg-error")) return "alert-circle";
    return role === "user" ? "user" : "cloud-sun";
  }

  function addBubble(role, text, extraClass) {
    const cls = extraClass || (role === "user" ? "msg-user" : "msg-assistant");
    const div = document.createElement("div");
    div.className = "msg " + cls;
    const iconWrap = document.createElement("span");
    iconWrap.className = "msg-icon";
    iconWrap.setAttribute("aria-hidden", "true");
    const icon = document.createElement("i");
    icon.setAttribute("data-lucide", messageIconName(role, extraClass));
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    iconWrap.appendChild(icon);
    div.appendChild(iconWrap);
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    lucideRefresh();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setTyping(on) {
    const id = "typing-indicator";
    document.getElementById(id)?.remove();
    if (!on) return;
    const wrap = document.createElement("div");
    wrap.id = id;
    wrap.className = "msg msg-assistant typing-wrap";
    wrap.innerHTML =
      '<span class="msg-icon" aria-hidden="true"><i data-lucide="cloud-sun"></i></span>' +
      '<div class="msg-bubble msg-bubble--typing">' +
      '<div class="typing" aria-label="…"><span></span><span></span><span></span></div>' +
      "</div>";
    messagesEl.appendChild(wrap);
    lucideRefresh();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  localeTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!localeMenu) return;
    if (localeMenu.hidden) openLocaleMenu();
    else closeLocaleMenu();
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
    const prev = getLocale();
    closeLocaleMenu();
    if (v === prev) return;
    setLocale(v);
    try {
      await loadI18n(v);
    } catch {
      /* ignore */
    }
    lucideRefresh();
  });

  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) {
      input.focus();
      return;
    }
    const loc = getLocale();
    input.value = "";
    autosize();
    addBubble("user", text);
    history.push({ role: "user", content: text });
    sendBtn.disabled = true;
    setTyping(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Locale": loc,
        },
        body: JSON.stringify({ messages: history, locale: loc }),
      });
      const data = await res.json().catch(() => ({}));
      setTyping(false);
      if (!res.ok) {
        addBubble("assistant", data.error || strings.errorGeneric || "Error", "msg-error");
        return;
      }
      const reply = data.reply || "";
      history.push({ role: "assistant", content: reply });
      addBubble("assistant", reply);
    } catch {
      setTyping(false);
      addBubble("assistant", strings.errorNetwork || "Network error", "msg-error");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  });

  const initial = getLocale();
  setLocale(initial);
  loadI18n(initial)
    .then(() => lucideRefresh())
    .catch(() => lucideRefresh());
})();
