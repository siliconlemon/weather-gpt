(function () {
  const STORAGE_KEY = "weather-gpt-locale";
  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("composer");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const localeSelect = document.getElementById("locale");

  let strings = {};
  const history = [];

  function getLocale() {
    const v = localStorage.getItem(STORAGE_KEY) || "cs";
    return v === "en" ? "en" : "cs";
  }

  function setLocale(loc) {
    localStorage.setItem(STORAGE_KEY, loc);
    document.documentElement.lang = loc;
    localeSelect.value = loc;
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
    document.title = strings.title || document.title;
  }

  function addBubble(role, text, extraClass) {
    const div = document.createElement("div");
    div.className = "msg " + (extraClass || (role === "user" ? "msg-user" : "msg-assistant"));
    div.textContent = text;
    messagesEl.appendChild(div);
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
      '<div class="typing" aria-label="…"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  localeSelect.addEventListener("change", async () => {
    const loc = localeSelect.value === "en" ? "en" : "cs";
    setLocale(loc);
    await loadI18n(loc);
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
    if (!text) return;
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
  loadI18n(initial).catch(() => {});
})();
