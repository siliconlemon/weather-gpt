(function (global) {
  "use strict";

  const history = [];
  let conversationEpoch = 0;

  /** @type {HTMLElement | null} */
  let messagesEl = null;
  /** @type {HTMLButtonElement | null} */
  let chatClearBtn = null;
  /** @type {HTMLElement | null} */
  let suggestionsEl = null;
  /** @type {HTMLTextAreaElement | null} */
  let input = null;
  /** @type {HTMLFormElement | null} */
  let form = null;
  /** @type {HTMLButtonElement | null} */
  let sendBtn = null;

  /** @type {() => Record<string, string>} */
  let getStrings = () => ({});
  /** @type {() => string} */
  let getLocale = () => "cs";
  /** @type {() => void} */
  let onLucide = () => {};

  function init(opts) {
    if (!opts) return;
    messagesEl = opts.messagesEl || null;
    chatClearBtn = opts.chatClearBtn || null;
    suggestionsEl = opts.suggestionsEl || null;
    input = opts.input || null;
    form = opts.form || null;
    sendBtn = opts.sendBtn || null;
    if (typeof opts.getStrings === "function") getStrings = opts.getStrings;
    if (typeof opts.getLocale === "function") getLocale = opts.getLocale;
    if (typeof opts.onLucide === "function") onLucide = opts.onLucide;

    chatClearBtn?.addEventListener("click", () => clearConversation());
    suggestionsEl?.addEventListener("click", onSuggestionsClick);
    input?.addEventListener("input", autosize);
    input?.addEventListener("keydown", onInputKeydown);
    form?.addEventListener("submit", onFormSubmit);
  }

  function onSuggestionsClick(e) {
    const btn = e.target.closest(".suggestion-chip");
    if (!btn || !suggestionsEl || !suggestionsEl.contains(btn) || !input || !form) return;
    const text = (btn.getAttribute("data-text") || "").trim();
    if (!text) return;
    input.value = text;
    autosize();
    form.requestSubmit();
  }

  function onInputKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey && form) {
      e.preventDefault();
      form.requestSubmit();
    }
  }

  function autosize() {
    if (!input) return;
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  function syncChatClearButton() {
    if (!chatClearBtn || !messagesEl) return;
    const bubbles = messagesEl.querySelectorAll(".msg:not(.typing-wrap)");
    const hasConversation = bubbles.length >= 2;
    chatClearBtn.hidden = !hasConversation;
  }

  function chatHasBubbles() {
    return !!(messagesEl && messagesEl.querySelector(".msg:not(.typing-wrap)"));
  }

  function pickRandomSubset(items, count) {
    const list = items.slice();
    for (let i = list.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = list[i];
      list[i] = list[j];
      list[j] = t;
    }
    return list.slice(0, Math.min(count, list.length));
  }

  function refreshStarterSuggestions() {
    if (!suggestionsEl) return;
    const all = getStrings().suggestions;
    if (!Array.isArray(all) || all.length === 0) {
      suggestionsEl.replaceChildren();
      return;
    }
    suggestionsEl.replaceChildren();
    for (const text of pickRandomSubset(all, 3)) {
      const btn = global.document.createElement("button");
      btn.type = "button";
      btn.className = "suggestion-chip";
      btn.setAttribute("data-text", text);
      btn.textContent = text;
      suggestionsEl.appendChild(btn);
    }
  }

  function syncSuggestionsStrip() {
    if (!suggestionsEl) return;
    if (chatHasBubbles()) {
      suggestionsEl.hidden = true;
      return;
    }
    refreshStarterSuggestions();
    suggestionsEl.hidden = suggestionsEl.childElementCount === 0;
  }

  function clearConversation() {
    conversationEpoch += 1;
    history.length = 0;
    if (messagesEl) messagesEl.innerHTML = "";
    setTyping(false);
    syncChatClearButton();
    syncSuggestionsStrip();
    onLucide();
    input?.focus();
  }

  function messageIconName(role, extraClass) {
    if (extraClass && extraClass.includes("msg-error")) return "alert-circle";
    return role === "user" ? "user" : "cloud-sun";
  }

  function fillBubbleContent(bubble, role, text, extraClass) {
    const err = extraClass && extraClass.includes("msg-error");
    const md = global.weatherGptMarkdown;
    if (role === "assistant" && !err && md && typeof md.tryFillAssistantBubble === "function") {
      if (md.tryFillAssistantBubble(bubble, text)) return;
    }
    bubble.classList.remove("msg-bubble--md");
    bubble.textContent = text;
  }

  function addBubble(role, text, extraClass) {
    if (!messagesEl) return;
    const cls = extraClass || (role === "user" ? "msg-user" : "msg-assistant");
    const div = global.document.createElement("div");
    div.className = "msg " + cls;
    const iconWrap = global.document.createElement("span");
    iconWrap.className = "msg-icon";
    iconWrap.setAttribute("aria-hidden", "true");
    const icon = global.document.createElement("i");
    icon.setAttribute("data-lucide", messageIconName(role, extraClass));
    const bubble = global.document.createElement("div");
    bubble.className = "msg-bubble";
    fillBubbleContent(bubble, role, text, extraClass);
    iconWrap.appendChild(icon);
    div.appendChild(iconWrap);
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    onLucide();
    messagesEl.scrollTop = messagesEl.scrollHeight;
    syncChatClearButton();
    syncSuggestionsStrip();
  }

  function setTyping(on) {
    if (!messagesEl) return;
    const id = "typing-indicator";
    global.document.getElementById(id)?.remove();
    if (!on) {
      syncChatClearButton();
      return;
    }
    const wrap = global.document.createElement("div");
    wrap.id = id;
    wrap.className = "msg msg-assistant typing-wrap";
    wrap.innerHTML =
      '<span class="msg-icon" aria-hidden="true"><i data-lucide="cloud-sun"></i></span>' +
      '<div class="msg-bubble msg-bubble--typing">' +
      '<div class="typing" aria-label="…"><span></span><span></span><span></span></div>' +
      "</div>";
    messagesEl.appendChild(wrap);
    onLucide();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function onFormSubmit(e) {
    e.preventDefault();
    if (!input || !form || !sendBtn) return;
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
    const epoch = conversationEpoch;
    const str = getStrings();
    try {
      const res = await global.fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Locale": loc,
        },
        body: JSON.stringify({ messages: history, locale: loc }),
      });
      if (epoch !== conversationEpoch) return;
      const data = await res.json().catch(() => ({}));
      if (epoch !== conversationEpoch) return;
      setTyping(false);
      if (!res.ok) {
        addBubble("assistant", data.error || str.errorGeneric || "Error", "msg-error");
        return;
      }
      const reply = data.reply || "";
      history.push({ role: "assistant", content: reply });
      addBubble("assistant", reply);
    } catch {
      if (epoch !== conversationEpoch) return;
      setTyping(false);
      addBubble("assistant", str.errorNetwork || "Network error", "msg-error");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  global.weatherGptChat = {
    init,
    syncChatClearButton,
    syncSuggestionsStrip,
    clearConversation,
  };
})(typeof window !== "undefined" ? window : globalThis);
