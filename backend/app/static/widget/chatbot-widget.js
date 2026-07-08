/*!
 * ChatBot Platform — embeddable widget
 * Usage:
 *   <script src="https://YOUR_BACKEND/widget/chatbot-widget.js"
 *           data-bot-key="PUBLIC_KEY" defer></script>
 *
 * The widget fetches its public config, decides (from the domain + display
 * rules) whether it should appear on the current page, and renders an isolated
 * chat bubble in a Shadow DOM so host-page CSS can never interfere.
 */
(function () {
  "use strict";

  // ---- locate our own <script> and read config attributes ----------------
  var script =
    document.currentScript ||
    (function () {
      var els = document.querySelectorAll("script[data-bot-key]");
      return els[els.length - 1];
    })();

  if (!script) return;

  var BOT_KEY = script.getAttribute("data-bot-key");
  if (!BOT_KEY) {
    console.error("[chatbot-widget] missing data-bot-key");
    return;
  }

  var API_BASE =
    script.getAttribute("data-api") ||
    (function () {
      try {
        return new URL(script.src).origin;
      } catch (e) {
        return "";
      }
    })();

  var SESSION_KEY = "chatbot_session_" + BOT_KEY;

  // ---- helpers ------------------------------------------------------------
  function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c];
    });
  }

  function normalizePath(p) {
    if (!p) return "/";
    p = p.replace(/\/+$/, "");
    return p === "" ? "/" : p;
  }

  function patternToPath(pattern) {
    var p = (pattern || "").trim();
    if (!p) return null;
    if (/^https?:\/\//i.test(p)) {
      try {
        p = new URL(p).pathname; // path only; ignore origin/query/hash
      } catch (e) {
        /* fall through with the raw value */
      }
    }
    p = p.replace(/[?#].*$/, ""); // drop any query string / hash
    if (!p) return null;
    if (p.charAt(0) !== "/") p = "/" + p;
    return p;
  }

  function pathMatches(pattern) {
    var target = patternToPath(pattern);
    if (target === null) return false;
    var current = normalizePath(window.location.pathname);
    if (target.indexOf("*") !== -1) {
      // Normalize the whole pattern once, then turn '*' into '.*'.
      // (Escaping per-segment AFTER splitting keeps '/blog/*' -> '^/blog/.*$'.)
      var norm = normalizePath(target);
      var rx = new RegExp(
        "^" + norm.split("*").map(escapeRegex).join(".*") + "$"
      );
      return rx.test(current);
    }
    return current === normalizePath(target);
  }

  // Extract a normalized hostname (lowercased, without a leading "www.")
  function hostOf(value) {
    if (!value) return "";
    var s = String(value).trim();
    if (!/^https?:\/\//i.test(s)) s = "https://" + s;
    var host;
    try {
      host = new URL(s).hostname;
    } catch (e) {
      host = String(value).trim();
    }
    return host.toLowerCase().replace(/^www\./, "");
  }

  // The bot only runs on the domain configured in the admin panel (site_url).
  // Empty site_url => no domain restriction (useful for local testing/demo).
  function domainMatches(siteUrl) {
    var want = hostOf(siteUrl);
    if (!want) return true;
    var have = window.location.hostname.toLowerCase().replace(/^www\./, "");
    return have === want || have.slice(-(want.length + 1)) === "." + want;
  }

  function shouldShow(cfg) {
    if (!cfg || cfg.is_active === false) return false;
    // 1) The current site's domain must match the configured site_url.
    if (!domainMatches(cfg.site_url)) {
      console.info(
        "[chatbot-widget] hidden: this page (" +
          window.location.hostname +
          ") does not match the configured site (" +
          cfg.site_url +
          ")."
      );
      return false;
    }
    // 2) Then apply the page display rules.
    var mode = cfg.display_mode || "all";
    var paths = cfg.display_paths || [];
    if (mode === "all") return true;
    var anyMatch = paths.some(pathMatches);
    if (mode === "only") return anyMatch;
    if (mode === "all_except") return !anyMatch;
    return true;
  }

  function getSessionId() {
    var id = null;
    try {
      id = window.localStorage.getItem(SESSION_KEY);
    } catch (e) {}
    if (!id) {
      id = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      try {
        window.localStorage.setItem(SESSION_KEY, id);
      } catch (e) {}
    }
    return id;
  }

  // ---- rendering ----------------------------------------------------------
  function render(cfg) {
    var accent = cfg.accent_color || "#4f46e5";
    var name = cfg.widget_title || "Assistant";
    var subtitle = cfg.bot_subtitle || "";
    var welcome = cfg.welcome_message || "Hi! How can I help you?";
    var logoUrl = cfg.logo_url || "";
    var quickReplies = Array.isArray(cfg.quick_replies) ? cfg.quick_replies : [];
    var linkButtons = Array.isArray(cfg.link_buttons) ? cfg.link_buttons : [];
    var footerText = cfg.footer_text || "";
    var launcherStyle = cfg.launcher_style || "circle"; // circle | icon | bar
    var launcherIconUrl = cfg.launcher_icon_url || "";
    var sessionId = getSessionId();

    var host = document.createElement("div");
    host.setAttribute("data-chatbot-widget", BOT_KEY);
    // Defensive inline styles: keep the host from becoming a containing block
    // for the fixed-position children (a page rule like `div{transform:...}`
    // would otherwise re-anchor the widget to this element instead of the viewport).
    host.style.cssText =
      "position: fixed; top: 0; left: 0; width: 0; height: 0; margin: 0; " +
      "padding: 0; border: 0; transform: none; filter: none; perspective: none; " +
      "contain: none; z-index: 2147483000;";
    document.body.appendChild(host);
    var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;

    var avatarInner = logoUrl
      ? '<img src="' + escapeHtml(logoUrl) + '" alt="">'
      : "<span>" + escapeHtml((name || "A").charAt(0).toUpperCase()) + "</span>";

    var chatIcon =
      '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
    var launcherImg =
      launcherStyle === "icon" ? launcherIconUrl || logoUrl : logoUrl;
    var launcherInner = launcherImg
      ? '<img src="' + escapeHtml(launcherImg) + '" alt="">'
      : chatIcon;

    var expandIcon =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';

    var newChatIcon =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>';

    var sendIcon =
      '<svg viewBox="0 0 24 24"><path d="M4 12h13M12 6l6 6-6 6" fill="none" ' +
      'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
      'stroke-linejoin="round"/></svg>';

    var style = document.createElement("style");
    style.textContent =
      ":host,*{box-sizing:border-box;}" +
      ".cbw *{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}" +
      /* launcher */
      ".cbw-launcher{position:fixed;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;" +
      "background:" + accent + ";color:#fff;border:none;cursor:pointer;box-shadow:0 8px 24px rgba(16,24,40,.22);" +
      "display:flex;align-items:center;justify-content:center;z-index:2147483000;transition:transform .15s ease;overflow:hidden;}" +
      ".cbw-launcher:hover{transform:scale(1.06);}" +
      ".cbw-launcher img{width:100%;height:100%;object-fit:cover;}" +
      ".cbw-launcher svg{width:28px;height:28px;fill:#fff;}" +
      ".cbw-launcher.cbw-style-icon{background:transparent;border-radius:16px;box-shadow:0 8px 24px rgba(16,24,40,.24);}" +
      /* panel */
      ".cbw-panel{position:fixed;bottom:92px;right:20px;width:384px;max-width:calc(100vw - 32px);height:600px;" +
      "max-height:calc(100vh - 120px);background:#fff;border-radius:18px;border:1px solid #101828;" +
      "box-shadow:0 24px 60px rgba(16,24,40,.28);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;}" +
      ".cbw-panel.cbw-open{display:flex;}" +
      ".cbw-panel.cbw-compact{height:auto;}" +
      ".cbw-panel.cbw-compact .cbw-body{display:none;}" +
      /* header */
      ".cbw-header{display:flex;align-items:center;gap:11px;padding:15px 16px 13px;border-bottom:1px solid #f0f1f3;}" +
      ".cbw-avatar{width:38px;height:38px;border-radius:50%;flex:none;background:" + accent + ";color:#fff;" +
      "display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;overflow:hidden;}" +
      ".cbw-avatar img{width:100%;height:100%;object-fit:cover;}" +
      ".cbw-hd{flex:1;min-width:0;}" +
      ".cbw-name{font-weight:700;font-size:15px;color:#101828;}" +
      ".cbw-sub{font-size:14px;color:#98a2b3;margin-left:7px;font-weight:400;}" +
      ".cbw-close{background:none;border:none;color:#98a2b3;font-size:22px;cursor:pointer;line-height:1;padding:0 2px;}" +
      ".cbw-close:hover{color:#475467;}" +
      ".cbw-expand{background:none;border:none;color:#98a2b3;cursor:pointer;padding:0 4px 0 2px;display:none;align-items:center;}" +
      ".cbw-expand svg{width:16px;height:16px;}" +
      ".cbw-expand:hover{color:#475467;}" +
      ".cbw-newchat{background:none;border:none;color:#98a2b3;cursor:pointer;padding:0 4px;display:inline-flex;align-items:center;}" +
      ".cbw-newchat svg{width:17px;height:17px;}" +
      ".cbw-newchat:hover{color:#475467;}" +
      /* body */
      ".cbw-body{flex:1;overflow-y:auto;padding:18px 16px;background:#fff;display:flex;flex-direction:column;gap:14px;}" +
      ".cbw-msg{font-size:14.5px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;}" +
      ".cbw-msg.bot{align-self:flex-start;max-width:85%;background:#f2f4f7;color:#1f2937;padding:9px 13px;" +
      "border-radius:14px;border-bottom-left-radius:4px;}" +
      ".cbw-msg.bot a{color:" + accent + ";}" +
      ".cbw-msg.bot p{margin:0 0 8px;}.cbw-msg.bot p:last-child{margin-bottom:0;}" +
      ".cbw-msg.bot ul,.cbw-msg.bot ol{margin:6px 0;padding-left:20px;}" +
      ".cbw-msg.bot img{max-width:100%;border-radius:8px;}" +
      ".cbw-msg.user{align-self:flex-end;max-width:82%;background:" + accent + ";color:#fff;padding:9px 13px;" +
      "border-radius:14px;border-bottom-right-radius:4px;}" +
      ".cbw-msg.err{align-self:flex-start;max-width:90%;background:#fef3f2;color:#b42318;border:1px solid #fecdca;" +
      "padding:9px 13px;border-radius:12px;}" +
      ".cbw-typing{align-self:flex-start;display:flex;gap:4px;padding:4px 2px;}" +
      ".cbw-typing span{width:7px;height:7px;border-radius:50%;background:#c4c7cf;animation:cbw-blink 1.2s infinite both;}" +
      ".cbw-typing span:nth-child(2){animation-delay:.2s;}.cbw-typing span:nth-child(3){animation-delay:.4s;}" +
      "@keyframes cbw-blink{0%,80%,100%{opacity:.3;}40%{opacity:1;}}" +
      /* quick replies */
      ".cbw-quick{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px 12px;}" +
      ".cbw-quick.cbw-hide{display:none;}" +
      ".cbw-quick button{background:" + accent + ";color:#fff;border:none;border-radius:8px;padding:9px 14px;" +
      "font-size:13.5px;font-weight:600;cursor:pointer;transition:opacity .15s;}" +
      ".cbw-quick button:hover{opacity:.9;}" +
      /* link buttons (navigate to a slug; shown in both compact & full) */
      ".cbw-links{display:flex;flex-direction:column;gap:8px;padding:0 16px 10px;}" +
      ".cbw-links:empty{display:none;}" +
      ".cbw-links button{background:" + accent + ";color:#fff;border:none;border-radius:8px;padding:10px 14px;" +
      "font-size:14px;font-weight:600;cursor:pointer;text-align:center;transition:opacity .15s;}" +
      ".cbw-links button:hover{opacity:.9;}" +
      /* input */
      ".cbw-inwrap{padding:8px 12px 6px;}" +
      ".cbw-inbox{display:flex;align-items:flex-end;gap:6px;border:1px solid #d0d5dd;border-radius:12px;" +
      "padding:6px 6px 6px 13px;background:#fff;transition:border-color .15s,box-shadow .15s;}" +
      ".cbw-inbox:focus-within{border-color:" + accent + ";box-shadow:0 0 0 3px " + accent + "22;}" +
      ".cbw-input{flex:1;resize:none;border:none;outline:none;font-size:14.5px;font-family:inherit;line-height:1.4;" +
      "padding:6px 0;max-height:110px;background:transparent;color:#101828;}" +
      ".cbw-send{flex:none;width:34px;height:34px;border-radius:8px;border:none;background:#f2f4f7;color:#475467;" +
      "cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .15s,color .15s;}" +
      ".cbw-send:hover:not(:disabled){background:" + accent + ";color:#fff;}" +
      ".cbw-send:disabled{opacity:.5;cursor:not-allowed;}" +
      ".cbw-send svg{width:18px;height:18px;}" +
      /* footer */
      ".cbw-foot{text-align:center;font-size:11.5px;color:#98a2b3;padding:2px 16px 12px;line-height:1.45;}";
    root.appendChild(style);

    var wrap = document.createElement("div");
    wrap.className = "cbw";
    wrap.innerHTML =
      '<button class="cbw-launcher cbw-style-' + launcherStyle + '" aria-label="Open chat">' +
      launcherInner + "</button>" +
      '<div class="cbw-panel" role="dialog" aria-label="Chat window">' +
      '<div class="cbw-header">' +
      '<div class="cbw-avatar">' + avatarInner + "</div>" +
      '<div class="cbw-hd"><span class="cbw-name"></span><span class="cbw-sub"></span></div>' +
      '<button class="cbw-newchat" aria-label="New chat" title="New chat">' + newChatIcon + "</button>" +
      '<button class="cbw-expand" aria-label="Expand">' + expandIcon + "</button>" +
      '<button class="cbw-close" aria-label="Close">&times;</button>' +
      "</div>" +
      '<div class="cbw-body"></div>' +
      '<div class="cbw-quick"></div>' +
      '<div class="cbw-links"></div>' +
      '<div class="cbw-inwrap"><div class="cbw-inbox">' +
      '<textarea class="cbw-input" rows="1" placeholder="Write a message..."></textarea>' +
      '<button class="cbw-send" aria-label="Send">' + sendIcon + "</button>" +
      "</div></div>" +
      '<div class="cbw-foot"></div>' +
      "</div>";
    root.appendChild(wrap);

    var launcher = root.querySelector(".cbw-launcher");
    var panel = root.querySelector(".cbw-panel");
    var closeBtn = root.querySelector(".cbw-close");
    var expandBtn = root.querySelector(".cbw-expand");
    var newChatBtn = root.querySelector(".cbw-newchat");
    var body = root.querySelector(".cbw-body");
    var input = root.querySelector(".cbw-input");
    var sendBtn = root.querySelector(".cbw-send");
    var quickWrap = root.querySelector(".cbw-quick");
    var linkWrap = root.querySelector(".cbw-links");
    var footEl = root.querySelector(".cbw-foot");

    root.querySelector(".cbw-name").textContent = name;
    var subEl = root.querySelector(".cbw-sub");
    if (subtitle) subEl.textContent = subtitle;
    else subEl.style.display = "none";

    if (footerText) footEl.textContent = footerText;
    else footEl.style.display = "none";

    input.setAttribute(
      "placeholder",
      name ? "Ask " + name + " a question" : "Write a message..."
    );

    var started = false;
    var busy = false;

    function scrollDown() {
      body.scrollTop = body.scrollHeight;
    }

    function addMsg(text, cls) {
      var el = document.createElement("div");
      el.className = "cbw-msg " + cls;
      // Bot replies may contain HTML (links, lists, etc.) and are rendered as
      // markup so e.g. an <a> is actually clickable. User/error text is escaped.
      if (cls === "bot") el.innerHTML = text;
      else el.textContent = text;
      body.appendChild(el);
      scrollDown();
      return el;
    }

    function showTyping() {
      var t = document.createElement("div");
      t.className = "cbw-typing";
      t.innerHTML = "<span></span><span></span><span></span>";
      body.appendChild(t);
      scrollDown();
      return t;
    }

    function hideQuick() {
      quickWrap.classList.add("cbw-hide");
    }

    if (quickReplies.length === 0) {
      quickWrap.style.display = "none";
    } else {
      quickReplies.forEach(function (q) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = q;
        b.addEventListener("click", function () {
          if (busy) return;
          input.value = q;
          send();
        });
        quickWrap.appendChild(b);
      });
    }

    // Link buttons: navigate to a slug (path or full URL). Shown in both modes.
    function navTo(slug) {
      var s = (slug || "").trim();
      if (!s) return;
      var target = /^https?:\/\//i.test(s)
        ? s
        : window.location.origin + (s.charAt(0) === "/" ? s : "/" + s);
      window.location.href = target;
    }
    linkButtons.forEach(function (lb) {
      if (!lb || !lb.text || !lb.slug) return;
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = lb.text;
      b.addEventListener("click", function () {
        navTo(lb.slug);
      });
      linkWrap.appendChild(b);
    });

    function showLauncher(v) {
      launcher.style.display = v ? "flex" : "none";
    }
    function ensureStarted() {
      if (started) return;
      started = true;
      // Load prior history for this visitor's session (persists across pages).
      fetch(
        API_BASE +
          "/v1/public/bots/" +
          encodeURIComponent(BOT_KEY) +
          "/history?session_id=" +
          encodeURIComponent(sessionId)
      )
        .then(function (r) {
          return r.ok ? r.json() : { messages: [] };
        })
        .then(function (data) {
          var msgs = (data && data.messages) || [];
          if (msgs.length) {
            hideQuick();
            msgs.forEach(function (m) {
              addMsg(m.content, m.role === "user" ? "user" : "bot");
            });
          } else {
            addMsg(welcome, "bot");
          }
        })
        .catch(function () {
          addMsg(welcome, "bot");
        });
    }

    function newChat() {
      // Start a fresh session; the previous conversation stays in the DB (owner keeps it).
      sessionId = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      try {
        window.localStorage.setItem(SESSION_KEY, sessionId);
      } catch (e) {}
      body.innerHTML = "";
      started = false;
      quickWrap.classList.remove("cbw-hide");
      showFull();
    }
    // Full chat view (with the message area).
    function showFull() {
      panel.classList.add("cbw-open");
      panel.classList.remove("cbw-compact");
      ensureStarted();
      showLauncher(false);
      input.focus();
    }
    // Compact box (header + quick replies + input + footer, no message area).
    function showCompact() {
      panel.classList.add("cbw-open");
      panel.classList.add("cbw-compact");
      showLauncher(false);
    }
    function hidePanel() {
      panel.classList.remove("cbw-open");
      showLauncher(true);
    }

    // Initial state depends on the launcher style.
    if (launcherStyle === "bar") {
      expandBtn.style.display = "inline-flex";
      showCompact();
    } else {
      showLauncher(true);
    }

    launcher.addEventListener("click", function () {
      if (launcherStyle === "bar") showCompact();
      else showFull();
    });
    closeBtn.addEventListener("click", hidePanel);
    expandBtn.addEventListener("click", function () {
      if (panel.classList.contains("cbw-compact")) showFull();
      else showCompact();
    });
    newChatBtn.addEventListener("click", newChat);

    input.addEventListener("input", function () {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 110) + "px";
    });

    function send() {
      var text = input.value.trim();
      if (!text || busy) return;
      // Sending from the compact box expands it into the full chat.
      if (panel.classList.contains("cbw-compact")) showFull();
      busy = true;
      sendBtn.disabled = true;
      hideQuick();
      addMsg(text, "user");
      input.value = "";
      input.style.height = "auto";
      var typing = showTyping();
      var botEl = null;
      var acc = "";

      function removeTyping() {
        if (typing) {
          typing.remove();
          typing = null;
        }
      }
      function fail(msg) {
        removeTyping();
        addMsg(msg || "Something went wrong. Please try again.", "err");
      }
      function handleEvent(jsonStr) {
        var data;
        try {
          data = JSON.parse(jsonStr);
        } catch (e) {
          return;
        }
        if (data.error) {
          fail(data.error);
          return;
        }
        if (data.done) return;
        if (data.delta) {
          removeTyping();
          if (!botEl) botEl = addMsg("", "bot");
          acc += data.delta;
          botEl.innerHTML = acc;
          scrollDown();
        }
      }
      function drain(buf) {
        var parts = buf.split("\n\n");
        var rest = parts.pop();
        parts.forEach(function (evt) {
          var line = evt.trim();
          if (line.indexOf("data:") === 0) handleEvent(line.slice(5).trim());
        });
        return rest;
      }

      fetch(API_BASE + "/v1/public/bots/" + encodeURIComponent(BOT_KEY) + "/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
        .then(function (resp) {
          if (!resp.ok) {
            return resp
              .json()
              .catch(function () {
                return {};
              })
              .then(function (d) {
                fail((d && (d.detail || d.message)) || "Something went wrong.");
              });
          }
          if (!resp.body || !resp.body.getReader) {
            // Fallback for browsers without streaming.
            return resp.text().then(function (t) {
              drain(t + "\n\n");
            });
          }
          var reader = resp.body.getReader();
          var decoder = new TextDecoder();
          var buffer = "";
          function pump() {
            return reader.read().then(function (res) {
              if (res.done) {
                drain(buffer + "\n\n");
                return;
              }
              buffer += decoder.decode(res.value, { stream: true });
              buffer = drain(buffer);
              return pump();
            });
          }
          return pump();
        })
        .catch(function () {
          fail("Network error. Please try again.");
        })
        .finally(function () {
          busy = false;
          sendBtn.disabled = false;
          input.focus();
        });
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });

    // Admin-authored custom CSS/JS. CSS is appended AFTER our base styles so the
    // admin's rules take priority. JS runs with the shadow root as `root`.
    if (cfg.custom_css) {
      var customStyle = document.createElement("style");
      customStyle.textContent = cfg.custom_css;
      root.appendChild(customStyle);
    }
    if (cfg.custom_js) {
      try {
        new Function("root", "widget", cfg.custom_js)(root, panel);
      } catch (e) {
        console.error("[chatbot-widget] custom JS error:", e);
      }
    }
  }

  // ---- boot ---------------------------------------------------------------
  function boot() {
    fetch(API_BASE + "/v1/public/bots/" + encodeURIComponent(BOT_KEY) + "/config")
      .then(function (res) {
        if (!res.ok) throw new Error("config " + res.status);
        return res.json();
      })
      .then(function (cfg) {
        if (shouldShow(cfg)) render(cfg);
      })
      .catch(function (err) {
        console.error("[chatbot-widget]", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
