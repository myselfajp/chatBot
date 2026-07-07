import { useEffect, useState } from "react";
import api, { errMsg } from "../../api/client";
import Layout from "../../components/Layout";
import { Badge, EmptyState, FullPageSpinner, Notice } from "../../components/ui";

const LIMIT = 50;

function looksLikeUrl(s) {
  if (!s || typeof s !== "string") return false;
  return /^https?:\/\//i.test(s) || /^[\w-]+(\.[\w-]+)+/.test(s.trim());
}

function hrefFor(s) {
  return /^https?:\/\//i.test(s) ? s : `https://${s}`;
}

function shortKey(key) {
  if (!key) return "—";
  return key.length > 10 ? `${key.slice(0, 10)}…` : key;
}

export default function AdminBots() {
  const [bots, setBots] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/v1/admin/bots", {
        params: { page, limit: LIMIT },
      });
      setBots(data.data || []);
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
  }, [page]);

  const hasNext = page * LIMIT < total;

  if (loading) {
    return (
      <Layout title="All Bots">
        <FullPageSpinner />
      </Layout>
    );
  }

  return (
    <Layout title="All Bots">
      <p className="muted mb-2" style={{ margin: 0 }}>
        {total} {total === 1 ? "bot" : "bots"} across all accounts.
      </p>

      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>

      {bots.length === 0 ? (
        <div className="card">
          <EmptyState title="No bots yet">
            No chatbots have been created on this platform yet.
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Site</th>
                  <th>Owner</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Public key</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {bots.map((bot) => (
                  <tr key={bot.id}>
                    <td style={{ fontWeight: 600 }}>
                      {bot.name || "Untitled bot"}
                    </td>
                    <td>
                      {looksLikeUrl(bot.site_url) ? (
                        <a
                          className="mono"
                          style={{ fontSize: 13 }}
                          href={hrefFor(bot.site_url)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {bot.site_url}
                        </a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="muted">{bot.owner_email || "—"}</td>
                    <td>
                      <Badge color="indigo">{bot.active_provider}</Badge>
                    </td>
                    <td>
                      <Badge color={bot.is_active ? "green" : "gray"}>
                        {bot.is_active ? "Active" : "Disabled"}
                      </Badge>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13 }}>
                        {shortKey(bot.public_key)}
                      </span>
                    </td>
                    <td className="muted">
                      {bot.created_at
                        ? new Date(bot.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="between mt-2">
            <span className="muted">Page {page}</span>
            <div className="row">
              <button
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Prev
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={!hasNext}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
