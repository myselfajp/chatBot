// Small shared presentational primitives used across pages.

export function Notice({ type = "info", children, onClose }) {
  if (!children) return null;
  return (
    <div className={`notice notice-${type}`}>
      <div className="between">
        <span>{children}</span>
        {onClose && (
          <span
            style={{ cursor: "pointer", fontWeight: 700, marginLeft: 8 }}
            onClick={onClose}
          >
            ×
          </span>
        )}
      </div>
    </div>
  );
}

export function Spinner({ dark = false }) {
  return <span className={`spin ${dark ? "spin-dark" : ""}`} />;
}

export function FullPageSpinner() {
  return (
    <div className="center-screen">
      <Spinner dark />
    </div>
  );
}

export function Badge({ children, color = "gray" }) {
  return <span className={`badge badge-${color}`}>{children}</span>;
}

export function Switch({ checked, onChange, disabled }) {
  return (
    <label className="switch">
      <input
        type="checkbox"
        checked={!!checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="slider" />
    </label>
  );
}

export function Field({ label, hint, children }) {
  return (
    <div className="field">
      {label && <label className="label">{label}</label>}
      {children}
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty">
      <h3 style={{ marginBottom: 6 }}>{title}</h3>
      <div>{children}</div>
    </div>
  );
}
