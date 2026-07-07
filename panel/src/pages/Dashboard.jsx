import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errMsg } from "../api/client";
import Layout from "../components/Layout";
import { Badge, EmptyState, Notice, Spinner } from "../components/ui";

const PROVIDER_LABELS = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [bots, setBots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/v1/bots");
      setBots(data.data || []);
      setError("");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createBot = async () => {
    setCreating(true);
    setError("");
    try {
      const { data } = await api.post("/v1/bots", {
        name: "New Chatbot",
        site_url: "",
      });
      navigate(`/bots/${data.id}`);
    } catch (err) {
      setError(errMsg(err));
      setCreating(false);
    }
  };

  const removeBot = async (bot) => {
    if (!window.confirm(`Delete "${bot.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/v1/bots/${bot.id}`);
      setBots((prev) => prev.filter((b) => b.id !== bot.id));
    } catch (err) {
      setError(errMsg(err));
    }
  };

  return (
    <Layout title="My Chatbots">
      <div className="between mb-2">
        <p className="muted mt-0" style={{ margin: 0 }}>
          Create a chatbot, configure it, and embed it on any website.
        </p>
        <button className="btn btn-primary" onClick={createBot} disabled={creating}>
          {creating ? <Spinner /> : "＋"} New chatbot
        </button>
      </div>

      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>

      {loading ? (
        <div className="card card-pad text-center">
          <Spinner dark />
        </div>
      ) : bots.length === 0 ? (
        <div className="card">
          <EmptyState title="No chatbots yet">
            Click <strong>New chatbot</strong> to create your first one.
          </EmptyState>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Website</th>
                <th>Provider</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bots.map((bot) => (
                <tr key={bot.id}>
                  <td>
                    <span
                      style={{ fontWeight: 600, cursor: "pointer" }}
                      onClick={() => navigate(`/bots/${bot.id}`)}
                    >
                      {bot.name || "Untitled bot"}
                    </span>
                  </td>
                  <td className="muted">
                    {bot.site_url ? (
                      <span className="mono" style={{ fontSize: 13 }}>
                        {bot.site_url}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <Badge color="indigo">
                      {PROVIDER_LABELS[bot.active_provider] || bot.active_provider}
                    </Badge>
                  </td>
                  <td>
                    <Badge color={bot.is_active ? "green" : "gray"}>
                      {bot.is_active ? "Active" : "Disabled"}
                    </Badge>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div className="row" style={{ justifyContent: "flex-end" }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/bots/${bot.id}`)}
                      >
                        Configure
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => removeBot(bot)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
