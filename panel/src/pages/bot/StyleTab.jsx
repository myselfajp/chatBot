import { useMemo, useRef, useState } from "react";
import api, { errMsg } from "../../api/client";
import { Field, Notice, Spinner } from "../../components/ui";

// Extract fenced ```css / ```js blocks from an assistant reply.
function extractBlock(text, langs) {
  const re = new RegExp("```(" + langs.join("|") + ")\\s*\\n([\\s\\S]*?)```", "i");
  const m = (text || "").match(re);
  return m ? m[2].trim() : "";
}

function buildPreview({ css, js, accent, name, subtitle, welcome }) {
  const a = accent || "#4f46e5";
  const initial = (name || "A").charAt(0).toUpperCase();
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#eef0f3;padding:14px;}
    .cbw-panel{width:100%;max-width:360px;margin:0 auto;background:#fff;border:1px solid #101828;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.15);}
    .cbw-header{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #f0f1f3;}
    .cbw-avatar{width:38px;height:38px;border-radius:50%;background:${a};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;}
    .cbw-name{font-weight:700;font-size:15px;color:#101828;}
    .cbw-sub{font-size:14px;color:#98a2b3;margin-left:6px;}
    .cbw-body{padding:16px;display:flex;flex-direction:column;gap:12px;min-height:180px;}
    .cbw-msg{font-size:14.5px;line-height:1.5;}
    .cbw-msg.bot{align-self:flex-start;max-width:85%;background:#f2f4f7;color:#1f2937;padding:9px 13px;border-radius:14px;border-bottom-left-radius:4px;}
    .cbw-msg.bot a{color:${a};}
    .cbw-msg.bot h1{font-size:20px;margin:0 0 6px;} .cbw-msg.bot h2{font-size:17px;margin:0 0 6px;}
    .cbw-msg.bot p{margin:0 0 8px;} .cbw-msg.bot ul{margin:6px 0;padding-left:20px;}
    .cbw-msg.user{align-self:flex-end;max-width:82%;background:${a};color:#fff;padding:9px 13px;border-radius:14px;border-bottom-right-radius:4px;}
    .cbw-quick{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px 10px;}
    .cbw-links{display:flex;flex-direction:column;gap:8px;padding:0 16px 10px;}
    .cbw-quick button,.cbw-links button{background:${a};color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:13.5px;font-weight:600;cursor:pointer;}
    .cbw-inwrap{padding:8px 12px;}
    .cbw-inbox{display:flex;align-items:center;gap:6px;border:1px solid #d0d5dd;border-radius:12px;padding:6px 6px 6px 12px;}
    .cbw-input{flex:1;border:none;outline:none;font-size:14.5px;}
    .cbw-send{width:34px;height:34px;border-radius:8px;border:none;background:#f2f4f7;color:#475467;cursor:pointer;}
    .cbw-foot{text-align:center;font-size:11.5px;color:#98a2b3;padding:4px 16px 12px;}
  </style></head><body>
    <div class="cbw-panel">
      <div class="cbw-header">
        <div class="cbw-avatar">${initial}</div>
        <div><span class="cbw-name">${name || "Assistant"}</span><span class="cbw-sub">${subtitle || ""}</span></div>
      </div>
      <div class="cbw-body">
        <div class="cbw-msg bot"><h1>Heading H1</h1><h2>Heading H2</h2><p>${welcome || "Hi! How can I help you today?"} Here is a <a href="#">link</a>.</p><ul><li>List item one</li><li>List item two</li></ul></div>
        <div class="cbw-msg user">This is a user message.</div>
        <div class="cbw-msg bot">Another bot message with <strong>bold</strong> text.</div>
      </div>
      <div class="cbw-quick"><button>Quick reply</button><button>Another</button></div>
      <div class="cbw-links"><button>Contact us</button></div>
      <div class="cbw-inwrap"><div class="cbw-inbox"><input class="cbw-input" placeholder="Ask a question"/><button class="cbw-send">&rarr;</button></div></div>
      <div class="cbw-foot">Footer disclaimer text</div>
    </div>
    <style>${css || ""}</style>
    <script>
      try { (function(root, widget){ ${js || ""} })(document, document.querySelector('.cbw-panel')); }
      catch(e){ console.error("custom JS error:", e); }
    </script>
  </body></html>`;
}

export default function StyleTab({ botId, form, setField }) {
  const [chat, setChat] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatErr, setChatErr] = useState("");
  const lastAssistant = useRef("");

  const previewHtml = useMemo(
    () =>
      buildPreview({
        css: form.custom_css,
        js: form.custom_js,
        accent: form.accent_color,
        name: form.widget_title,
        subtitle: form.bot_subtitle,
        welcome: form.welcome_message,
      }),
    [
      form.custom_css,
      form.custom_js,
      form.accent_color,
      form.widget_title,
      form.bot_subtitle,
      form.welcome_message,
    ]
  );

  const suggestedCss = extractBlock(lastAssistant.current, ["css"]);
  const suggestedJs = extractBlock(lastAssistant.current, ["js", "javascript"]);

  const sendToAssistant = async () => {
    const text = chatInput.trim();
    if (!text || chatBusy) return;
    const next = [...chat, { role: "user", content: text }];
    setChat(next);
    setChatInput("");
    setChatBusy(true);
    setChatErr("");
    try {
      const { data } = await api.post(`/v1/bots/${botId}/style-assistant`, {
        messages: next,
      });
      lastAssistant.current = data.reply || "";
      setChat([...next, { role: "assistant", content: data.reply || "" }]);
    } catch (err) {
      setChatErr(errMsg(err));
      setChat(next);
    } finally {
      setChatBusy(false);
    }
  };

  return (
    <div>
      <div className="grid-2" style={{ alignItems: "start" }}>
        {/* Left: editors + assistant */}
        <div>
          <div className="card card-pad mb-2">
            <Field
              label="Custom CSS"
              hint="Applied on top of the default widget styles (yours win). Targets classes like .cbw-msg.bot, .cbw-send, .cbw-quick button."
            >
              <textarea
                className="textarea mono"
                rows={8}
                value={form.custom_css}
                onChange={(e) => setField("custom_css", e.target.value)}
                placeholder={".cbw-msg.bot { background: #eef; }\n.cbw-send { border-radius: 50%; }"}
              />
            </Field>
            <Field
              label="Custom JS"
              hint="Runs inside the widget with the shadow root as `root` (e.g. root.querySelector('.cbw-header'))."
            >
              <textarea
                className="textarea mono"
                rows={6}
                value={form.custom_js}
                onChange={(e) => setField("custom_js", e.target.value)}
                placeholder={"// root.querySelector('.cbw-name').textContent = 'Hello';"}
              />
            </Field>
            <p className="hint">Press “Save changes” (top) to apply to the live widget.</p>
          </div>

          <div className="card card-pad">
            <h3 style={{ marginTop: 0, marginBottom: 4 }}>Styling assistant</h3>
            <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>
              Describe the look you want; it only helps with widget CSS/JS.
            </p>
            <Notice type="error" onClose={() => setChatErr("")}>
              {chatErr}
            </Notice>
            <div
              style={{
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: 12,
                maxHeight: 260,
                overflowY: "auto",
                background: "#fafafb",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                marginBottom: 10,
              }}
            >
              {chat.length === 0 && (
                <span className="muted" style={{ fontSize: 13 }}>
                  e.g. “Make bot messages purple with rounded corners and a bigger send button.”
                </span>
              )}
              {chat.map((m, i) => (
                <div
                  key={i}
                  style={{
                    alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                    background: m.role === "user" ? "var(--primary)" : "#fff",
                    color: m.role === "user" ? "#fff" : "var(--text)",
                    border: m.role === "user" ? "none" : "1px solid var(--border)",
                    padding: "8px 12px",
                    borderRadius: 12,
                    maxWidth: "90%",
                    whiteSpace: "pre-wrap",
                    fontSize: 13,
                  }}
                >
                  {m.content}
                </div>
              ))}
              {chatBusy && (
                <span className="muted" style={{ fontSize: 13 }}>
                  <Spinner dark /> thinking…
                </span>
              )}
            </div>
            {(suggestedCss || suggestedJs) && (
              <div className="row mb-1">
                {suggestedCss && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setField("custom_css", suggestedCss)}
                  >
                    Insert CSS
                  </button>
                )}
                {suggestedJs && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setField("custom_js", suggestedJs)}
                  >
                    Insert JS
                  </button>
                )}
              </div>
            )}
            <div className="row">
              <input
                className="input"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendToAssistant()}
                placeholder="Describe the style you want…"
              />
              <button className="btn btn-primary" onClick={sendToAssistant} disabled={chatBusy}>
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Right: live preview */}
        <div className="card card-pad">
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Live preview</h3>
          <iframe
            title="widget-preview"
            srcDoc={previewHtml}
            sandbox="allow-scripts"
            style={{
              width: "100%",
              height: 560,
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "#eef0f3",
            }}
          />
          <p className="hint">Updates as you type. Shows a sample of every element.</p>
        </div>
      </div>
    </div>
  );
}
