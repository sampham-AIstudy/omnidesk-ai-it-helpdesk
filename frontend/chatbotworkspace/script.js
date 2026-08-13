(() => {
  "use strict";

  // ============ State ============
  const state = {
    conversations: [],
    activeId: null,
    thinking: false,
  };

  const LS_KEY = "nova.conversations";
  const LS_THEME = "nova.theme";

  // ============ Elements ============
  const els = {
    sidebar: document.getElementById("sidebar"),
    conversationList: document.getElementById("conversationList"),
    emptyConv: document.getElementById("emptyConv"),
    newChatBtn: document.getElementById("newChatBtn"),
    chatHeader: document.getElementById("chatHeader"),
    headerTitle: document.getElementById("headerTitle"),
    chatArea: document.getElementById("chatArea"),
    welcome: document.getElementById("welcome"),
    messages: document.getElementById("messages"),
    userInput: document.getElementById("userInput"),
    sendBtn: document.getElementById("sendBtn"),
    attachBtn: document.getElementById("attachBtn"),
    themeBtn: document.getElementById("themeBtn"),
  };

  // ============ Storage ============
  function loadState() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      state.conversations = raw ? JSON.parse(raw) : [];
    } catch {
      state.conversations = [];
    }
    const theme = localStorage.getItem(LS_THEME) || "light";
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.setAttribute("color-scheme", theme);
  }

  function saveState() {
    localStorage.setItem(LS_KEY, JSON.stringify(state.conversations));
  }

  // ============ Markdown renderer ============
  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }

  function renderMarkdown(text) {
    const blocks = [];
    const lines = text.split("\n");
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Code block
      if (line.trim().startsWith("```")) {
        const buf = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          buf.push(lines[i]);
          i++;
        }
        i++;
        blocks.push(`<pre><code>${escapeHtml(buf.join("\n"))}</code></pre>`);
        continue;
      }

      // Heading
      const h = line.match(/^(#{1,3})\s+(.*)$/);
      if (h) {
        const lvl = h[1].length;
        blocks.push(`<h${lvl}>${renderInline(h[2])}</h${lvl}>`);
        i++;
        continue;
      }

      // Blockquote
      if (line.trim().startsWith(">")) {
        const buf = [];
        while (i < lines.length && lines[i].trim().startsWith(">")) {
          buf.push(lines[i].trim().replace(/^>\s?/, ""));
          i++;
        }
        blocks.push(`<blockquote>${renderInline(buf.join(" "))}</blockquote>`);
        continue;
      }

      // List
      if (/^\s*[-*]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          items.push(`<li>${renderInline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`);
          i++;
        }
        blocks.push(`<ul>${items.join("")}</ul>`);
        continue;
      }

      // Ordered list
      if (/^\s*\d+\.\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
          items.push(`<li>${renderInline(lines[i].replace(/^\s*\d+\.\s+/, ""))}</li>`);
          i++;
        }
        blocks.push(`<ol>${items.join("")}</ol>`);
        continue;
      }

      // Blank line
      if (line.trim() === "") {
        i++;
        continue;
      }

      // Paragraph (accumulate consecutive text lines)
      const buf = [];
      while (
        i < lines.length &&
        lines[i].trim() !== "" &&
        !lines[i].trim().startsWith("```") &&
        !/^\s*[-*]\s+/.test(lines[i]) &&
        !/^\s*\d+\.\s+/.test(lines[i]) &&
        !/^(#{1,3})\s+/.test(lines[i])
      ) {
        buf.push(lines[i]);
        i++;
      }
      blocks.push(`<p>${renderInline(buf.join(" "))}</p>`);
    }

    return blocks.join("");
  }

  // ============ Rendering messages ============
  function createMsgEl(role, content) {
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}`;

    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = role === "user" ? "You" : "Nova";
    wrap.appendChild(label);

    const body = document.createElement("div");
    body.className = "msg-content";
    body.innerHTML = role === "assistant" ? renderMarkdown(content) : escapeHtml(content).replace(/\n/g, "<br>");
    wrap.appendChild(body);

    if (role === "assistant") {
      const actions = document.createElement("div");
      actions.className = "msg-actions";
      actions.innerHTML =
        '<button class="copy-btn" title="Copy response">' +
        '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>' +
        "</svg>Copy</button>" +
        '<button class="regenerate-btn" title="Regenerate response">' +
        '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>' +
        "</svg>Regenerate</button>";
      wrap.appendChild(actions);

      actions.querySelector(".copy-btn").addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(content);
          const btn = actions.querySelector(".copy-btn");
          const original = btn.innerHTML;
          btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>Copied';
          setTimeout(() => (btn.innerHTML = original), 1600);
        } catch {
          /* clipboard unavailable */
        }
      });

      actions.querySelector(".regenerate-btn").addEventListener("click", () => {
        const idx = Array.from(els.messages.children).indexOf(wrap);
        regenerate(idx);
      });
    }

    return wrap;
  }

  function renderConversation(conv) {
    els.messages.innerHTML = "";
    els.welcome.classList.add("hidden");
    els.chatHeader.classList.remove("hidden");
    els.headerTitle.textContent = conv.title || "New chat";
    conv.messages.forEach((m) => {
      els.messages.appendChild(createMsgEl(m.role, m.content));
    });
    scrollToBottom();
  }

  function showWelcome() {
    els.messages.innerHTML = "";
    els.welcome.classList.remove("hidden");
    els.chatHeader.classList.add("hidden");
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      els.chatArea.scrollTop = els.chatArea.scrollHeight;
    });
  }

  // ============ Conversations ============
  function getActive() {
    return state.conversations.find((c) => c.id === state.activeId) || null;
  }

  function newConversation() {
    const conv = {
      id: "conv_" + Date.now(),
      title: "New chat",
      messages: [],
      createdAt: Date.now(),
    };
    state.conversations.unshift(conv);
    state.activeId = conv.id;
    saveState();
    renderSidebar();
    showWelcome();
    els.userInput.focus();
  }

  function renderSidebar() {
    els.conversationList.innerHTML = "";
    const items = els.conversationList.querySelector(".empty-conv");
    if (items) items.remove();

    if (state.conversations.length === 0) {
      const p = document.createElement("p");
      p.className = "empty-conv";
      p.textContent = "No conversations yet";
      els.conversationList.appendChild(p);
      return;
    }

    state.conversations.forEach((conv) => {
      const btn = document.createElement("button");
      btn.className = "conv-item" + (conv.id === state.activeId ? " active" : "");
      btn.title = conv.title;

      const text = document.createElement("span");
      text.className = "conv-text";
      text.textContent = conv.title;
      btn.appendChild(text);

      const del = document.createElement("button");
      del.className = "conv-del";
      del.title = "Delete conversation";
      del.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>';
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      });
      btn.appendChild(del);

      btn.addEventListener("click", () => {
        state.activeId = conv.id;
        renderSidebar();
        renderConversation(conv);
        els.userInput.focus();
      });

      els.conversationList.appendChild(btn);
    });
  }

  function deleteConversation(id) {
    state.conversations = state.conversations.filter((c) => c.id !== id);
    if (state.activeId === id) {
      state.activeId = null;
      if (state.conversations.length > 0) {
        state.activeId = state.conversations[0].id;
      }
    }
    saveState();
    renderSidebar();
    if (state.activeId) {
      renderConversation(getActive());
    } else {
      showWelcome();
    }
  }

  // ============ Bot simulation ============
  const RESPONSES = [
    {
      match: /(trip|travel|da nang|du lịch|plan)/i,
      reply: (q) => `Here's a suggested **3-day Da Nang itinerary**:

1. **Day 1 — City & River** — Explore Han Market, visit the Marble Mountains, then take a sunset walk across the **Dragon Bridge**.
2. **Day 2 — Beaches & Peninsula** — Morning at My Khe Beach, afternoon hike to **Son Tra Peninsula**, and try fresh seafood at a local spot.
3. **Day 3 — Ba Na Hills** — Spend the day at Sun World Ba Na Hills, ride the Golden Bridge, then catch a night flight back.

> Tip: Book Ba Na Hills tickets online a day ahead to skip the queue. The best weather is between **February and August**.`,
    },
    {
      match: /(python|script|code|code snippet)/i,
      reply: (q) => `Sure! Here's a Python script that **sorts files into folders by extension**:

\`\`\`python
import os
import shutil
from pathlib import Path

def sort_files(directory):
    directory = Path(directory)
    for file in directory.iterdir():
        if file.is_file():
            folder = file.suffix.lstrip('.') or 'no_extension'
            target = directory / folder
            target.mkdir(exist_ok=True)
            shutil.move(str(file), str(target / file.name))

if __name__ == "__main__":
    sort_files(input("Folder path: "))
\`\`\`

Run it, pass a folder path, and files get grouped into subfolders named after their extension.`,
    },
    {
      match: /(react|vue|svelte|frontend|framework)/i,
      reply: (q) => `Here's a quick **React vs Vue** comparison for 2026:

| Aspect | React | Vue |
|---|---|---|
| **Learning curve** | Moderate | Gentle |
| **Ecosystem** | Massive | Growing fast |
| **State management** | Redux / Zustand | Pinia / Vuex |
| **Performance** | Excellent | Excellent |
| **Use cases** | Large apps, full control | Medium apps, rapid dev |

**Bottom line:** pick **React** if you want the largest ecosystem and job market. Pick **Vue** if you value simplicity and developer ergonomics. Both are great choices — it mostly comes down to team familiarity.`,
    },
    {
      match: /(photosynthesis|plant|light|carbon)/i,
      reply: (q) => `Photosynthesis is how **plants make their own food** using sunlight. Here's the simple version:

- Plants take in **carbon dioxide** from the air through tiny pores in their leaves.
- They absorb **water** from the soil through their roots.
- Sunlight hits the green pigment **chlorophyll** in the leaves.
- The plant combines these ingredients to make **sugar (glucose)** — its food — and releases **oxygen** as a byproduct.

In one line: **sunlight + water + CO₂ → sugar + oxygen**. That's why trees are so important — they produce the oxygen we breathe.`,
    },
  ];

  const FALLBACKS = [
    (q) => `Great question. To give you a useful answer, could you tell me a bit more context?

Here's what I understood from your message:

> ${q}

If you're looking for **code**, a **plan**, or an **explanation**, just say so and I'll tailor my response.`,
    (q) => `I'm still in demo mode, but here's how I'd approach **"${q}"**:

1. **Clarify the goal** — what does success look like?
2. **Break it into steps** — small, testable pieces.
3. **Iterate** — measure, adjust, repeat.

Want me to expand on any of these steps in detail?`,
    (q) => `That's an interesting topic! In a real setup I'd answer this from my knowledge base.

For now, you can try one of the **suggestion cards** above — each one shows off a different response style (itinerary, code, comparison table, and explanation).`,
  ];

  function makeReply(question) {
    const clean = question.trim().toLowerCase();
    for (const r of RESPONSES) {
      if (r.match.test(clean)) return r.reply(clean);
    }
    return FALLBACKS[Math.floor(Math.random() * FALLBACKS.length)](clean);
  }

  // ============ Send / regenerate ============
  function addMessage(role, content) {
    const conv = getActive();
    if (!conv) return;
    conv.messages.push({ role, content });
    if (role === "user" && conv.title === "New chat") {
      conv.title = content.length > 42 ? content.slice(0, 42) + "…" : content;
    }
    saveState();
    renderSidebar();
    els.messages.appendChild(createMsgEl(role, content));
    scrollToBottom();
  }

  function send() {
    const text = els.userInput.value.trim();
    if (!text || state.thinking) return;
    if (!state.activeId) newConversation();
    if (!state.activeId) return;

    els.welcome.classList.add("hidden");
    els.chatHeader.classList.remove("hidden");
    els.headerTitle.textContent = getActive().title;

    addMessage("user", text);
    els.userInput.value = "";
    autoResize();
    setThinking(true);

    const typingWrap = document.createElement("div");
    typingWrap.className = "msg assistant typing";
    typingWrap.innerHTML =
      '<div class="msg-label">Nova</div>' +
      '<div class="msg-content"><div class="dots"><span></span><span></span><span></span></div></div>';
    els.messages.appendChild(typingWrap);
    scrollToBottom();

    const delay = 900 + Math.random() * 900;
    setTimeout(() => {
      typingWrap.remove();
      const reply = makeReply(text);
      addMessage("assistant", reply);
      setThinking(false);
    }, delay);
  }

  function regenerate(msgIndex) {
    if (state.thinking) return;
    const conv = getActive();
    if (!conv || conv.messages.length < 2) return;

    const lastUser = conv.messages[msgIndex - 1];
    if (!lastUser || lastUser.role !== "user") return;

    conv.messages = conv.messages.slice(0, msgIndex);
    saveState();
    renderConversation(conv);
    setThinking(true);

    const typingWrap = document.createElement("div");
    typingWrap.className = "msg assistant typing";
    typingWrap.innerHTML =
      '<div class="msg-label">Nova</div>' +
      '<div class="msg-content"><div class="dots"><span></span><span></span><span></span></div></div>';
    els.messages.appendChild(typingWrap);
    scrollToBottom();

    const delay = 900 + Math.random() * 900;
    setTimeout(() => {
      typingWrap.remove();
      addMessage("assistant", makeReply(lastUser.content));
      setThinking(false);
    }, delay);
  }

  function setThinking(val) {
    state.thinking = val;
    els.sendBtn.disabled = val;
  }

  // ============ Auto-resize textarea ============
  function autoResize() {
    els.userInput.style.height = "auto";
    els.userInput.style.height = Math.min(els.userInput.scrollHeight, 200) + "px";
  }

  // ============ Events ============
  els.sendBtn.addEventListener("click", send);

  els.userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  els.userInput.addEventListener("input", autoResize);

  els.newChatBtn.addEventListener("click", () => newConversation());

  els.attachBtn.addEventListener("click", () => {
    els.attachBtn.style.transform = "scale(0.9)";
    setTimeout(() => (els.attachBtn.style.transform = ""), 120);
  });

  els.themeBtn.addEventListener("click", () => {
    const next =
      document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    document.documentElement.setAttribute("color-scheme", next);
    localStorage.setItem(LS_THEME, next);
  });

  document.querySelectorAll(".suggestion-card").forEach((card) => {
    card.addEventListener("click", () => {
      els.userInput.value = card.dataset.prompt;
      autoResize();
      send();
    });
  });

  // ============ Init ============
  loadState();
  renderSidebar();

  if (state.activeId && getActive()) {
    renderConversation(getActive());
  } else {
    showWelcome();
  }

  els.userInput.focus();
})();
