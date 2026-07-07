import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Icon({ children }) {
  return <span style={{ width: 18, textAlign: "center" }}>{children}</span>;
}

export default function Layout({ children, title }) {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const initial = (user?.full_name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo-dot">✦</span>
          <span>ChatBot</span>
        </div>

        <nav className="nav">
          <NavLink to="/" end className="nav-item">
            <Icon>🤖</Icon> My Chatbots
          </NavLink>

          {isAdmin && (
            <>
              <div className="nav-section">Admin</div>
              <NavLink to="/admin/users" className="nav-item">
                <Icon>👥</Icon> Users
              </NavLink>
              <NavLink to="/admin/bots" className="nav-item">
                <Icon>📊</Icon> All Bots
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-foot">
          <div className="user-chip">
            <div className="avatar">{initial}</div>
            <div style={{ overflow: "hidden" }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 13,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {user?.full_name || "Account"}
              </div>
              <div className="muted" style={{ fontSize: 12 }}>
                {isAdmin ? "Administrator" : "Customer"}
              </div>
            </div>
          </div>
          <button className="btn btn-ghost btn-block btn-sm" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <h1 className="page-title">{title}</h1>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate("/")}>
            Dashboard
          </button>
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
