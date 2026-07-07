import { useEffect, useState } from "react";
import api, { errMsg } from "../../api/client";
import Layout from "../../components/Layout";
import { Badge, EmptyState, Field, Notice, Spinner, Switch } from "../../components/ui";

const PAGE_SIZE = 20;

const PASSWORD_HINT =
  "Min 8 characters, at least one uppercase, one lowercase, and one digit.";

const emptyForm = {
  full_name: "",
  email: "",
  phone_number: "",
  password: "",
  role: "customer",
  is_active: true,
};

// Shared form fields for both create and edit flows.
function UserForm({ initial, isEdit, saving, submitLabel, onSubmit, onCancel }) {
  const [form, setForm] = useState(initial);
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const submit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={submit}>
      <div className="grid-2">
        <Field label="Full name">
          <input
            className="input"
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            required
          />
        </Field>
        <Field label="Email">
          <input
            className="input"
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            required
          />
        </Field>
      </div>

      <div className="grid-2">
        <Field label="Phone number">
          <input
            className="input"
            value={form.phone_number}
            onChange={(e) => set("phone_number", e.target.value)}
          />
        </Field>
        <Field
          label={isEdit ? "New password" : "Password"}
          hint={isEdit ? `${PASSWORD_HINT} Leave blank to keep current.` : PASSWORD_HINT}
        >
          <input
            className="input"
            type="password"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            required={!isEdit}
          />
        </Field>
      </div>

      <div className="grid-2">
        <Field label="Role">
          <select
            className="select"
            value={form.role}
            onChange={(e) => set("role", e.target.value)}
          >
            <option value="customer">customer</option>
            <option value="admin">admin</option>
          </select>
        </Field>
        <Field label="Active">
          <Switch checked={form.is_active} onChange={(c) => set("is_active", c)} />
        </Field>
      </div>

      <div className="row mt-1" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? <Spinner /> : submitLabel}
        </button>
      </div>
    </form>
  );
}

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/v1/admin/users", {
        params: { page, limit: PAGE_SIZE, search },
      });
      const payload = data.data || {};
      setUsers(payload.users || []);
      setTotal(payload.total || 0);
      setTotalPages(payload.total_pages || 1);
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
  }, [page, search]);

  const runSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const openCreate = () => {
    setEditing(null);
    setFormError("");
    setShowCreate(true);
  };

  const openEdit = (u) => {
    setShowCreate(false);
    setFormError("");
    setEditing(u);
  };

  const createUser = async (form) => {
    setSaving(true);
    setFormError("");
    try {
      await api.post("/v1/admin/users", {
        full_name: form.full_name,
        email: form.email,
        phone_number: form.phone_number,
        password: form.password,
        role: form.role,
        is_active: form.is_active,
      });
      setShowCreate(false);
      await load();
    } catch (err) {
      setFormError(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const updateUser = async (form) => {
    if (!editing) return;
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        full_name: form.full_name,
        email: form.email,
        phone_number: form.phone_number,
        role: form.role,
        is_active: form.is_active,
      };
      if (form.password) payload.password = form.password;
      await api.put(`/v1/admin/users/${editing.id}`, payload);
      setEditing(null);
      await load();
    } catch (err) {
      setFormError(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const removeUser = async (u) => {
    if (!window.confirm(`Delete ${u.email}? This cannot be undone.`)) return;
    try {
      await api.delete(`/v1/admin/users/${u.id}`);
      await load();
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const editInitial = editing
    ? {
        full_name: editing.full_name || "",
        email: editing.email || "",
        phone_number: editing.phone_number || "",
        password: "",
        role: editing.role || "customer",
        is_active: !!editing.is_active,
      }
    : emptyForm;

  return (
    <Layout title="Users">
      <div className="between mb-2">
        <form onSubmit={runSearch} className="row" style={{ flex: 1, maxWidth: 420 }}>
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="Search by name or email…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button className="btn btn-secondary" type="submit">
            Search
          </button>
        </form>
        <button className="btn btn-primary" onClick={openCreate}>
          ＋ New user
        </button>
      </div>

      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>

      {showCreate && (
        <div className="card card-pad mb-2">
          <div className="between mb-2">
            <h3 style={{ margin: 0 }}>New user</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>
              ×
            </button>
          </div>
          <Notice type="error" onClose={() => setFormError("")}>
            {formError}
          </Notice>
          <UserForm
            initial={emptyForm}
            saving={saving}
            submitLabel="Create user"
            onSubmit={createUser}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      {loading ? (
        <div className="card card-pad text-center">
          <Spinner dark />
        </div>
      ) : users.length === 0 ? (
        <div className="card">
          <EmptyState title="No users found">
            {search
              ? "No users match your search."
              : "Click ＋ New user to create the first account."}
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 600 }}>{u.full_name || "—"}</td>
                    <td className="muted">
                      <span className="mono" style={{ fontSize: 13 }}>
                        {u.email}
                      </span>
                    </td>
                    <td>
                      <Badge color={u.role === "admin" ? "indigo" : "gray"}>{u.role}</Badge>
                    </td>
                    <td>
                      <Badge color={u.is_active ? "green" : "gray"}>
                        {u.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => openEdit(u)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => removeUser(u)}
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

          <div className="between mt-2">
            <span className="muted" style={{ fontSize: 13 }}>
              Page {page} of {totalPages} · {total} user{total === 1 ? "" : "s"}
            </span>
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
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {editing && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
            zIndex: 50,
          }}
          onClick={() => setEditing(null)}
        >
          <div
            className="card card-pad"
            style={{ width: "100%", maxWidth: 480 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="between mb-2">
              <h3 style={{ margin: 0 }}>Edit user</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setEditing(null)}>
                ×
              </button>
            </div>
            <Notice type="error" onClose={() => setFormError("")}>
              {formError}
            </Notice>
            <UserForm
              initial={editInitial}
              isEdit
              saving={saving}
              submitLabel="Save changes"
              onSubmit={updateUser}
              onCancel={() => setEditing(null)}
            />
          </div>
        </div>
      )}
    </Layout>
  );
}
