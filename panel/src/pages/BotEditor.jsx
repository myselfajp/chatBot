import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { API_BASE, errMsg } from "../api/client";
import Layout from "../components/Layout";
import { Badge, Field, FullPageSpinner, Notice, Spinner, Switch } from "../components/ui";

const PROVIDERS = [
  {
    key: "openai",
    label: "OpenAI",
    modelPlaceholder: "gpt-4o-mini",
    keyPlaceholder: "sk-...",
    docs: "Any OpenAI chat model id.",
  },
  {
    key: "anthropic",
    label: "Anthropic",
    modelPlaceholder: "claude-sonnet-5",
    keyPlaceholder: "sk-ant-...",
    docs: "Any Anthropic Claude model id.",
  },
  {
    key: "deepseek",
    label: "DeepSeek",
    modelPlaceholder: "deepseek-chat",
    keyPlaceholder: "sk-...",
    docs: "Any DeepSeek model id.",
  },
];

const TABS = ["General", "Prompt", "Feed Data", "Providers", "Embed & Test"];

const DISPLAY_MODES = [
  {
    value: "all",
    title: "Show on all pages",
    desc: "The chatbot appears everywhere on the site.",
  },
  {
    value: "all_except",
    title: "Show on all pages except…",
    desc: "The chatbot appears everywhere except the paths you list below.",
  },
  {
    value: "only",
    title: "Show only on specific pages",
    desc: "The chatbot appears only on the paths you list below.",
  },
];

const emptyForm = {
  name: "",
  site_url: "",
  display_mode: "all",
  displayPathsText: "",
  system_prompt: "",
  feed_data: "",
  active_provider: "openai",
  widget_title: "",
  bot_subtitle: "",
  logo_url: "",
  welcome_message: "",
  quickRepliesText: "",
  link_buttons: [],
  footer_text: "",
  accent_color: "#4f46e5",
  launcher_style: "circle",
  launcher_icon_url: "",
  is_active: true,
};

const LAUNCHER_STYLES = [
  {
    value: "circle",
    title: "Round button",
    desc: "A round floating button in the corner (uses your logo, or a chat icon).",
  },
  {
    value: "icon",
    title: "Custom icon",
    desc: "Upload your own image to use as the floating launcher.",
  },
  {
    value: "bar",
    title: "Compact chat box",
    desc: "A small chat box is always visible, with an expand button to open the full chat.",
  },
];

export default function BotEditor() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState("General");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState("");

  // Sitemap -> feed
  const [showSitemap, setShowSitemap] = useState(false);
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [sitemapMax, setSitemapMax] = useState(15);
  const [sitemapJob, setSitemapJob] = useState(null);
  const [sitemapBusy, setSitemapBusy] = useState(false);

  const [publicKey, setPublicKey] = useState("");
  const [embedSnippet, setEmbedSnippet] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [providers, setProviders] = useState([]);
  const [keyInputs, setKeyInputs] = useState({
    openai: "",
    anthropic: "",
    deepseek: "",
  });

  const applyBot = (bot) => {
    setPublicKey(bot.public_key);
    setEmbedSnippet(bot.embed_snippet || "");
    setForm({
      name: bot.name || "",
      site_url: bot.site_url || "",
      display_mode: bot.display_mode || "all",
      displayPathsText: (bot.display_paths || []).join("\n"),
      system_prompt: bot.system_prompt || "",
      feed_data: bot.feed_data || "",
      active_provider: bot.active_provider || "openai",
      widget_title: bot.widget_title || "",
      bot_subtitle: bot.bot_subtitle || "",
      logo_url: bot.logo_url || "",
      welcome_message: bot.welcome_message || "",
      quickRepliesText: (bot.quick_replies || []).join("\n"),
      link_buttons: Array.isArray(bot.link_buttons) ? bot.link_buttons : [],
      footer_text: bot.footer_text || "",
      accent_color: bot.accent_color || "#4f46e5",
      launcher_style: bot.launcher_style || "circle",
      launcher_icon_url: bot.launcher_icon_url || "",
      is_active: bot.is_active !== false,
    });
    setProviders(bot.providers || []);
    setKeyInputs({ openai: "", anthropic: "", deepseek: "" });
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/v1/bots/${id}`);
        applyBot(data);
      } catch (err) {
        setError(errMsg(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const setField = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const addLinkButton = () =>
    setForm((f) => ({
      ...f,
      link_buttons: [...(f.link_buttons || []), { text: "", slug: "" }],
    }));
  const updateLinkButton = (i, key, val) =>
    setForm((f) => ({
      ...f,
      link_buttons: f.link_buttons.map((b, idx) =>
        idx === i ? { ...b, [key]: val } : b
      ),
    }));
  const removeLinkButton = (i) =>
    setForm((f) => ({
      ...f,
      link_buttons: f.link_buttons.filter((_, idx) => idx !== i),
    }));

  const uploadImage = async (fieldKey, e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = ""; // allow re-picking the same file
    if (!file) return;
    setUploading(fieldKey);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`/v1/bots/${id}/upload`, fd);
      setField(fieldKey, data.url);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setUploading("");
    }
  };

  const setProvider = (providerKey, patch) =>
    setProviders((prev) =>
      prev.map((p) => (p.provider === providerKey ? { ...p, ...patch } : p))
    );

  const providerByKey = useMemo(() => {
    const map = {};
    providers.forEach((p) => (map[p.provider] = p));
    return map;
  }, [providers]);

  const save = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const payload = {
        name: form.name,
        site_url: form.site_url,
        display_mode: form.display_mode,
        display_paths: form.displayPathsText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        system_prompt: form.system_prompt,
        feed_data: form.feed_data,
        active_provider: form.active_provider,
        widget_title: form.widget_title,
        bot_subtitle: form.bot_subtitle,
        logo_url: form.logo_url,
        welcome_message: form.welcome_message,
        quick_replies: form.quickRepliesText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        link_buttons: (form.link_buttons || [])
          .map((b) => ({ text: (b.text || "").trim(), slug: (b.slug || "").trim() }))
          .filter((b) => b.text && b.slug),
        footer_text: form.footer_text,
        accent_color: form.accent_color,
        launcher_style: form.launcher_style,
        launcher_icon_url: form.launcher_icon_url,
        is_active: form.is_active,
        providers: PROVIDERS.map((p) => {
          const row = providerByKey[p.key] || {};
          const out = {
            provider: p.key,
            enabled: !!row.enabled,
            model: row.model || "",
          };
          const typed = (keyInputs[p.key] || "").trim();
          if (typed) out.api_key = typed;
          return out;
        }),
      };
      const { data } = await api.put(`/v1/bots/${id}`, payload);
      applyBot(data);
      setSuccess("Saved successfully.");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const copyEmbed = () => {
    navigator.clipboard?.writeText(embedSnippet);
    setSuccess("Embed code copied to clipboard.");
  };

  const startSitemap = async () => {
    const url = sitemapUrl.trim();
    if (!url || sitemapBusy) return;
    setSitemapBusy(true);
    setError("");
    setSuccess("");
    setSitemapJob({ status: "queued", pages_done: 0, pages_total: 0, items_added: 0 });
    try {
      const maxPages = Math.max(1, Math.min(200, Number(sitemapMax) || 15));
      const { data } = await api.post(`/v1/bots/${id}/feed/sitemap`, {
        sitemap_url: url,
        max_pages: maxPages,
      });
      let job = data;
      for (let i = 0; i < 800 && job.status !== "done" && job.status !== "error"; i++) {
        await new Promise((r) => setTimeout(r, 2500));
        const res = await api.get(`/v1/bots/${id}/feed/jobs/${data.id}`);
        job = res.data;
        setSitemapJob(job);
      }
      if (job.status === "done") {
        // Refresh just the feed field with the server-appended items.
        const botRes = await api.get(`/v1/bots/${id}`);
        setField("feed_data", botRes.data.feed_data || "");
        setSuccess(job.message || "Feed generated from the sitemap.");
      } else if (job.status === "error") {
        setError(job.message || "Sitemap import failed.");
      }
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setSitemapBusy(false);
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <Layout title="Configure Chatbot">
      <div className="between mb-2">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>
          ← Back to chatbots
        </button>
        <div className="row">
          <span className="muted" style={{ fontSize: 13 }}>
            {form.is_active ? "Active" : "Disabled"}
          </span>
          <Switch
            checked={form.is_active}
            onChange={(v) => setField("is_active", v)}
          />
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? <Spinner /> : null} Save changes
          </button>
        </div>
      </div>

      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>
      <Notice type="success" onClose={() => setSuccess("")}>
        {success}
      </Notice>

      <div className="tabs">
        {TABS.map((t) => (
          <div
            key={t}
            className={`tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </div>
        ))}
      </div>

      {/* ---------------- General ---------------- */}
      {tab === "General" && (
        <div className="card card-pad">
          <Field label="Chatbot name">
            <input
              className="input"
              value={form.name}
              onChange={(e) => setField("name", e.target.value)}
              placeholder="e.g. Store Assistant"
            />
          </Field>
          <Field
            label="Website URL (main domain)"
            hint="The chatbot will ONLY appear and work on this domain (and its subdomains), e.g. https://example.com. Leave blank to allow any domain (useful while testing)."
          >
            <input
              className="input mono"
              value={form.site_url}
              onChange={(e) => setField("site_url", e.target.value)}
              placeholder="https://example.com"
            />
          </Field>

          <div className="label mt-2">Where should the chatbot appear?</div>
          {DISPLAY_MODES.map((m) => (
            <label
              key={m.value}
              className="card"
              style={{
                display: "block",
                padding: "12px 14px",
                marginBottom: 10,
                cursor: "pointer",
                borderColor:
                  form.display_mode === m.value ? "var(--primary)" : "var(--border)",
              }}
            >
              <div className="row">
                <input
                  type="radio"
                  name="display_mode"
                  checked={form.display_mode === m.value}
                  onChange={() => setField("display_mode", m.value)}
                />
                <div>
                  <div style={{ fontWeight: 600 }}>{m.title}</div>
                  <div className="muted" style={{ fontSize: 13 }}>
                    {m.desc}
                  </div>
                </div>
              </div>
            </label>
          ))}

          {form.display_mode !== "all" && (
            <Field
              label={
                form.display_mode === "only"
                  ? "Show only on these paths / URLs"
                  : "Hide on these paths / URLs"
              }
              hint="One per line. Use paths like /pricing or /blog/* (wildcards allowed), or full URLs."
            >
              <textarea
                className="textarea mono"
                rows={5}
                value={form.displayPathsText}
                onChange={(e) => setField("displayPathsText", e.target.value)}
                placeholder={"/checkout\n/account/*\nhttps://example.com/private"}
              />
            </Field>
          )}
        </div>
      )}

      {/* ---------------- Prompt ---------------- */}
      {tab === "Prompt" && (
        <div className="card card-pad">
          <Field
            label="System prompt"
            hint="The core rules and persona: how the bot should behave, its tone, what it should and shouldn't do."
          >
            <textarea
              className="textarea"
              rows={14}
              value={form.system_prompt}
              onChange={(e) => setField("system_prompt", e.target.value)}
              placeholder="You are a friendly support assistant for Acme Inc. Answer concisely and politely. If you don't know an answer, offer to connect the user with a human."
            />
          </Field>
        </div>
      )}

      {/* ---------------- Feed Data ---------------- */}
      {tab === "Feed Data" && (
        <div className="card card-pad">
          <div className="between mb-1">
            <label className="label" style={{ margin: 0 }}>
              Source (feed) data
            </label>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowSitemap((s) => !s)}
            >
              🌐 Read from site
            </button>
          </div>

          {showSitemap && (
            <div
              className="card card-pad mb-2"
              style={{ background: "#fafafb" }}
            >
              <Field
                label="Sitemap URL"
                hint="We read each page listed in the sitemap and use your active provider to auto-generate FAQ items — each tagged with its source page. More pages = more time and provider cost."
              >
                <div className="row">
                  <input
                    className="input mono"
                    style={{ flex: 1 }}
                    value={sitemapUrl}
                    onChange={(e) => setSitemapUrl(e.target.value)}
                    placeholder="https://example.com/sitemap.xml"
                  />
                  <input
                    className="input"
                    type="number"
                    min={1}
                    max={200}
                    style={{ width: 96 }}
                    value={sitemapMax}
                    onChange={(e) => setSitemapMax(e.target.value)}
                    title="Max pages to read (1–200)"
                  />
                  <button
                    className="btn btn-primary"
                    disabled={sitemapBusy}
                    onClick={startSitemap}
                  >
                    {sitemapBusy ? <Spinner /> : "Generate"}
                  </button>
                </div>
              </Field>
              <div className="hint" style={{ marginTop: -8 }}>
                Max pages (1–200). Default 15.
              </div>
              {sitemapJob && (
                <div className="hint" style={{ marginTop: 4 }}>
                  Status: <strong>{sitemapJob.status}</strong>
                  {sitemapJob.pages_total > 0 &&
                    ` — read ${sitemapJob.pages_done}/${sitemapJob.pages_total} pages`}
                  {sitemapJob.items_added > 0 &&
                    `, ${sitemapJob.items_added} items added`}
                  {sitemapJob.message ? ` — ${sitemapJob.message}` : ""}
                </div>
              )}
              <p className="hint" style={{ marginBottom: 0 }}>
                Generated items are appended below with a{" "}
                <span className="mono">(Source: …)</span> line. Review, then press
                Save.
              </p>
            </div>
          )}

          <Field hint="Paste the knowledge the bot should answer from — FAQs, product info, policies, etc. The bot uses this as its source instead of crawling your whole site.">
            <textarea
              className="textarea"
              rows={16}
              value={form.feed_data}
              onChange={(e) => setField("feed_data", e.target.value)}
              placeholder={
                "Q: What are your shipping times?\nA: 2-4 business days within the EU.\n\nReturns: accepted within 30 days of purchase..."
              }
            />
          </Field>
        </div>
      )}

      {/* ---------------- Providers ---------------- */}
      {tab === "Providers" && (
        <div>
          <p className="muted mt-0">
            Enable the providers you want, enter the model id and API key for each,
            then choose which one this chatbot uses.
          </p>
          {PROVIDERS.map((p) => {
            const row = providerByKey[p.key] || {};
            const isActive = form.active_provider === p.key;
            return (
              <div
                key={p.key}
                className="card card-pad mb-2"
                style={{
                  borderColor: isActive ? "var(--primary)" : "var(--border)",
                }}
              >
                <div className="between mb-1">
                  <div className="row">
                    <strong style={{ fontSize: 15 }}>{p.label}</strong>
                    {isActive && <Badge color="indigo">Active</Badge>}
                    {row.has_key && <Badge color="green">Key set</Badge>}
                  </div>
                  <div className="row">
                    <span className="muted" style={{ fontSize: 13 }}>
                      Enabled
                    </span>
                    <Switch
                      checked={!!row.enabled}
                      onChange={(v) => setProvider(p.key, { enabled: v })}
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <Field label="Model" hint={p.docs}>
                    <input
                      className="input mono"
                      value={row.model || ""}
                      onChange={(e) => setProvider(p.key, { model: e.target.value })}
                      placeholder={p.modelPlaceholder}
                    />
                  </Field>
                  <Field
                    label="API key"
                    hint={
                      row.has_key
                        ? `Saved (${row.key_hint}). Leave blank to keep it.`
                        : "Stored encrypted. Never shown again."
                    }
                  >
                    <input
                      className="input mono"
                      type="password"
                      autoComplete="new-password"
                      value={keyInputs[p.key]}
                      onChange={(e) =>
                        setKeyInputs((k) => ({ ...k, [p.key]: e.target.value }))
                      }
                      placeholder={row.has_key ? "••••••••" : p.keyPlaceholder}
                    />
                  </Field>
                </div>

                <label className="row" style={{ cursor: "pointer", marginTop: 4 }}>
                  <input
                    type="radio"
                    name="active_provider"
                    checked={isActive}
                    onChange={() => setField("active_provider", p.key)}
                  />
                  <span>Use this provider for the chatbot</span>
                </label>
              </div>
            );
          })}
        </div>
      )}

      {/* ---------------- Embed & Test ---------------- */}
      {tab === "Embed & Test" && (
        <div>
          <div className="card card-pad mb-2">
            <h3 style={{ marginBottom: 12 }}>Widget appearance</h3>

            {/* Live header preview */}
            <div
              className="row mb-2"
              style={{
                gap: 11,
                padding: "12px 14px",
                border: "1px solid var(--border)",
                borderRadius: 12,
                background: "#fff",
              }}
            >
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: "50%",
                  flex: "none",
                  background: form.accent_color,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  overflow: "hidden",
                }}
              >
                {form.logo_url ? (
                  <img
                    src={form.logo_url}
                    alt=""
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                ) : (
                  (form.widget_title || "A").charAt(0).toUpperCase()
                )}
              </div>
              <div>
                <span style={{ fontWeight: 700 }}>
                  {form.widget_title || "Assistant"}
                </span>
                {form.bot_subtitle && (
                  <span className="muted" style={{ marginLeft: 7 }}>
                    {form.bot_subtitle}
                  </span>
                )}
              </div>
            </div>

            <div className="grid-2">
              <Field label="Bot name">
                <input
                  className="input"
                  value={form.widget_title}
                  onChange={(e) => setField("widget_title", e.target.value)}
                  placeholder="e.g. Webster"
                />
              </Field>
              <Field label="Role / subtitle">
                <input
                  className="input"
                  value={form.bot_subtitle}
                  onChange={(e) => setField("bot_subtitle", e.target.value)}
                  placeholder="e.g. Product Specialist"
                />
              </Field>
            </div>

            <Field
              label="Logo image"
              hint="Shown as the avatar in the widget header. Paste a URL or upload an image (PNG/JPG/GIF/WEBP, max 2 MB). Leave blank to use the bot name's initial."
            >
              <div className="row">
                <input
                  className="input mono"
                  style={{ flex: 1 }}
                  value={form.logo_url}
                  onChange={(e) => setField("logo_url", e.target.value)}
                  placeholder="https://example.com/logo.png"
                />
                <label className="btn btn-secondary" style={{ cursor: "pointer" }}>
                  {uploading === "logo_url" ? <Spinner dark /> : "Upload"}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    style={{ display: "none" }}
                    onChange={(e) => uploadImage("logo_url", e)}
                  />
                </label>
              </div>
            </Field>

            <Field label="Accent color">
              <div className="row">
                <input
                  type="color"
                  value={form.accent_color}
                  onChange={(e) => setField("accent_color", e.target.value)}
                  style={{
                    width: 44,
                    height: 40,
                    padding: 2,
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    background: "#fff",
                  }}
                />
                <input
                  className="input mono"
                  style={{ maxWidth: 140 }}
                  value={form.accent_color}
                  onChange={(e) => setField("accent_color", e.target.value)}
                />
              </div>
            </Field>

            <Field label="Welcome message">
              <textarea
                className="textarea"
                rows={2}
                value={form.welcome_message}
                onChange={(e) => setField("welcome_message", e.target.value)}
                placeholder="Hi! How can I help you today?"
              />
            </Field>

            <Field
              label="Quick reply buttons"
              hint="One per line. Sent as a chat message when tapped; hidden after the first reply."
            >
              <textarea
                className="textarea"
                rows={3}
                value={form.quickRepliesText}
                onChange={(e) => setField("quickRepliesText", e.target.value)}
                placeholder={"How do I get started?\nTalk to a human"}
              />
            </Field>

            <Field
              label="Link buttons"
              hint="Shown in both the compact and full widget. Clicking navigates to the slug — a path like /contact or a full URL. Add as many as you like."
            >
              {(form.link_buttons || []).map((b, i) => (
                <div className="row mb-1" key={i}>
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    placeholder="Button text (e.g. Contact us)"
                    value={b.text}
                    onChange={(e) => updateLinkButton(i, "text", e.target.value)}
                  />
                  <input
                    className="input mono"
                    style={{ flex: 1 }}
                    placeholder="/contact or https://…"
                    value={b.slug}
                    onChange={(e) => updateLinkButton(i, "slug", e.target.value)}
                  />
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => removeLinkButton(i)}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" onClick={addLinkButton}>
                ＋ Add button
              </button>
            </Field>

            <Field
              label="Footer note (optional)"
              hint="Small text under the input, e.g. a privacy disclaimer."
            >
              <input
                className="input"
                value={form.footer_text}
                onChange={(e) => setField("footer_text", e.target.value)}
                placeholder="By continuing you agree to our privacy policy."
              />
            </Field>

            <p className="hint">Remember to press “Save changes” after editing.</p>
          </div>

          {/* Launcher (collapsed state) */}
          <div className="card card-pad mb-2">
            <h3 style={{ marginBottom: 4 }}>Launcher (collapsed state)</h3>
            <p className="muted" style={{ marginTop: 0 }}>
              How the widget looks before it’s opened.
            </p>
            {LAUNCHER_STYLES.map((s) => (
              <label
                key={s.value}
                className="card"
                style={{
                  display: "block",
                  padding: "12px 14px",
                  marginBottom: 10,
                  cursor: "pointer",
                  borderColor:
                    form.launcher_style === s.value
                      ? "var(--primary)"
                      : "var(--border)",
                }}
              >
                <div className="row">
                  <input
                    type="radio"
                    name="launcher_style"
                    checked={form.launcher_style === s.value}
                    onChange={() => setField("launcher_style", s.value)}
                  />
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.title}</div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {s.desc}
                    </div>
                  </div>
                </div>
              </label>
            ))}

            {form.launcher_style === "icon" && (
              <Field
                label="Launcher icon image"
                hint="The image shown as the floating launcher. Paste a URL or upload (PNG/JPG/GIF/WEBP, max 2 MB)."
              >
                <div className="row">
                  <input
                    className="input mono"
                    style={{ flex: 1 }}
                    value={form.launcher_icon_url}
                    onChange={(e) => setField("launcher_icon_url", e.target.value)}
                    placeholder="https://example.com/launcher.png"
                  />
                  <label className="btn btn-secondary" style={{ cursor: "pointer" }}>
                    {uploading === "launcher_icon_url" ? <Spinner dark /> : "Upload"}
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/gif,image/webp"
                      style={{ display: "none" }}
                      onChange={(e) => uploadImage("launcher_icon_url", e)}
                    />
                  </label>
                </div>
              </Field>
            )}
          </div>

          <div className="card card-pad mb-2">
            <h3 style={{ marginBottom: 6 }}>Embed on your website</h3>
            <p className="muted" style={{ marginTop: 0 }}>
              Paste this snippet just before <span className="mono">&lt;/body&gt;</span>{" "}
              on any page of your site.
            </p>
            <div className="code-box">{embedSnippet}</div>
            <div className="row mt-2">
              <button className="btn btn-secondary btn-sm" onClick={copyEmbed}>
                Copy code
              </button>
              <span className="muted" style={{ fontSize: 13 }}>
                Public key: <span className="mono">{publicKey}</span>
              </span>
            </div>
            <p className="hint">
              The widget only appears when the page’s domain matches the{" "}
              <strong>Website URL</strong> set in the General tab
              {form.site_url ? (
                <>
                  {" "}(<span className="mono">{form.site_url}</span>)
                </>
              ) : null}
              , and when the page matches your display rules.
            </p>
          </div>

          <BotTester publicKey={publicKey} />
        </div>
      )}
    </Layout>
  );
}

/** Live tester that calls the public chat endpoint (verifies real config). */
function BotTester({ publicKey }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sessionId = useMemo(
    () => "panel-test-" + Math.random().toString(36).slice(2),
    []
  );

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    try {
      const { data } = await api.post(
        `/v1/public/bots/${encodeURIComponent(publicKey)}/chat`,
        { session_id: sessionId, message: text }
      );
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card card-pad">
      <h3 style={{ marginBottom: 6 }}>Test your chatbot</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Sends a real message through your active provider. Save your changes first.
      </p>
      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: 12,
          minHeight: 120,
          maxHeight: 300,
          overflowY: "auto",
          background: "#fafafb",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: 12,
        }}
      >
        {messages.length === 0 && (
          <span className="muted" style={{ fontSize: 13 }}>
            No messages yet. Say hello 👋
          </span>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "var(--primary)" : "#fff",
              color: m.role === "user" ? "#fff" : "var(--text)",
              border: m.role === "user" ? "none" : "1px solid var(--border)",
              padding: "8px 12px",
              borderRadius: 12,
              maxWidth: "80%",
              whiteSpace: "pre-wrap",
              fontSize: 14,
            }}
          >
            {m.content}
          </div>
        ))}
        {busy && (
          <span className="muted" style={{ fontSize: 13 }}>
            <Spinner dark /> thinking…
          </span>
        )}
      </div>
      <div className="row">
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type a test message…"
        />
        <button className="btn btn-primary" onClick={send} disabled={busy}>
          Send
        </button>
      </div>
    </div>
  );
}
