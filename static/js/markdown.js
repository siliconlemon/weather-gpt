/**
 * Assistant reply Markdown: normalize model quirks, parse with marked, sanitize with DOMPurify.
 * Depends on globals from vendor/marked.min.js and vendor/purify.min.js (load this file after both).
 */
(function (global) {
  "use strict";

  /** If the whole reply is one ``` fenced block, use inner text as Markdown. */
  function unwrapOuterCodeFence(s) {
    const t = s.trim();
    if (!t.startsWith("```")) return s;
    const nl = t.indexOf("\n");
    if (nl === -1) return s;
    const body = t.slice(nl + 1);
    const close = body.lastIndexOf("```");
    if (close === -1) return s;
    return body.slice(0, close).trim();
  }

  /**
   * Models often indent paragraphs (4+ spaces). In CommonMark that starts a code block, so ** stays literal.
   * Strip leading whitespace only before obvious Markdown block starts (**bold, bullets, numbered lists).
   */
  function stripAccidentalIndentBeforeMarkdown(s) {
    let t = s;
    t = t.replace(/^(?:[ \t]{1,})+(?=\*\*(?!\*))/, "");
    t = t.replace(/(\n\n)(?:[ \t]{1,})+(?=\*\*(?!\*))/g, "\n\n");
    t = t.replace(/(\n)(?:[ \t]{1,})+(?=\*\*(?!\*))/g, "\n");
    t = t.replace(/(\n\n)(?:[ \t]{1,})+(?=[-*+] )/g, "\n\n");
    t = t.replace(/(\n)(?:[ \t]{1,})+(?=[-*+] )/g, "\n");
    t = t.replace(/(\n\n)(?:[ \t]{1,})+(?=\d{1,3}\.\s)/g, "\n\n");
    t = t.replace(/(\n)(?:[ \t]{1,})+(?=\d{1,3}\.\s)/g, "\n");
    return t;
  }

  function normalizeAssistantMarkdown(src) {
    let s = (src || "").replace(/\r\n/g, "\n");
    s = unwrapOuterCodeFence(s);
    s = stripAccidentalIndentBeforeMarkdown(s);
    return s;
  }

  function depsAvailable() {
    return (
      typeof global.marked !== "undefined" &&
      typeof global.marked.parse === "function" &&
      typeof global.DOMPurify !== "undefined" &&
      typeof global.DOMPurify.sanitize === "function"
    );
  }

  /**
   * Renders assistant Markdown into bubble (innerHTML + msg-bubble--md).
   * @returns {boolean} true if rendered; false to fall back to plain textContent
   */
  function tryFillAssistantBubble(bubble, text) {
    if (!depsAvailable()) return false;
    try {
      bubble.classList.add("msg-bubble--md");
      const md = normalizeAssistantMarkdown(text);
      const raw = global.marked.parse(md, { async: false });
      const html = typeof raw === "string" ? raw : String(raw);
      bubble.innerHTML = global.DOMPurify.sanitize(html);
      return true;
    } catch {
      bubble.classList.remove("msg-bubble--md");
      return false;
    }
  }

  global.weatherGptMarkdown = { tryFillAssistantBubble };
})(typeof window !== "undefined" ? window : globalThis);
