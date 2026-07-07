import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { errMsg } from "../api/client";
import { Field, Notice, Spinner } from "../components/ui";

const PASSWORD_HINT =
  "At least 8 characters, with one uppercase letter, one lowercase letter, and one digit.";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const token = sp.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/v1/auth/reset-password", {
        token,
        new_password: newPassword,
      });
      setDone(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-dot">✦</span>
          <span>ChatBot</span>
        </div>
        <div className="auth-sub">Choose a new password</div>

        {!token ? (
          <>
            <Notice type="error">Invalid or missing reset token.</Notice>
            <div className="auth-foot">
              <Link to="/forgot-password">Request a new link</Link>
            </div>
          </>
        ) : done ? (
          <>
            <Notice type="success">
              Your password has been reset. Redirecting to sign in…
            </Notice>
            <div className="auth-foot">
              <Link to="/login">Sign in</Link>
            </div>
          </>
        ) : (
          <form onSubmit={submit}>
            <Notice type="error" onClose={() => setError("")}>
              {error}
            </Notice>

            <Field label="New password" hint={PASSWORD_HINT}>
              <input
                className="input"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>

            <Field label="Confirm new password">
              <input
                className="input"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>

            <button
              className="btn btn-primary btn-block"
              type="submit"
              disabled={submitting}
            >
              {submitting ? <Spinner /> : "Reset password"}
            </button>

            <div className="auth-foot">
              <Link to="/login">Back to sign in</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
