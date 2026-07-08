import { useEffect, useState } from "react";
import api, { errMsg } from "../../api/client";
import { EmptyState, Notice, Spinner } from "../../components/ui";

export default function ConversationsTab({ botId }) {
  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null); // conversation detail
  const [detailLoading, setDetailLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/v1/bots/${botId}/conversations`, {
        params: { page: 1, limit: 50 },
      });
      setList(data.data || []);
      setTotal(data.total || 0);
      setError("");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [botId]);

  const openConversation = async (cid) => {
    setDetailLoading(true);
    setActive(null);
    try {
      const { data } = await api.get(`/v1/bots/${botId}/conversations/${cid}`);
      setActive(data);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setDetailLoading(false);
    }
  };

  const fmt = (d) => (d ? new Date(d).toLocaleString() : "");

  return (
    <div>
      <p className="muted mt-0">
        {total} conversation{total === 1 ? "" : "s"}. These are kept even when a
        visitor starts a new chat.
      </p>
      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>

      {loading ? (
        <div className="card card-pad text-center">
          <Spinner dark />
        </div>
      ) : list.length === 0 ? (
        <div className="card">
          <EmptyState title="No conversations yet">
            Messages people send through the widget will appear here.
          </EmptyState>
        </div>
      ) : (
        <div className="grid-2" style={{ alignItems: "start" }}>
          {/* List */}
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>First message</th>
                  <th>Msgs</th>
                  <th>Last</th>
                </tr>
              </thead>
              <tbody>
                {list.map((c) => (
                  <tr
                    key={c.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => openConversation(c.id)}
                  >
                    <td>{c.preview || "—"}</td>
                    <td>{c.message_count}</td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {fmt(c.last_message_at || c.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Detail */}
          <div className="card card-pad">
            {detailLoading ? (
              <div className="text-center">
                <Spinner dark />
              </div>
            ) : !active ? (
              <div className="muted">Select a conversation to read it.</div>
            ) : (
              <div>
                <div className="muted mb-2" style={{ fontSize: 12 }}>
                  Session {active.session_id} · {fmt(active.created_at)}
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    maxHeight: 460,
                    overflowY: "auto",
                  }}
                >
                  {active.messages.map((m, i) => (
                    <div
                      key={i}
                      style={{
                        alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                        background: m.role === "user" ? "var(--primary)" : "#f2f4f7",
                        color: m.role === "user" ? "#fff" : "var(--text)",
                        padding: "8px 12px",
                        borderRadius: 12,
                        maxWidth: "85%",
                        whiteSpace: "pre-wrap",
                        fontSize: 14,
                      }}
                    >
                      {m.content}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
