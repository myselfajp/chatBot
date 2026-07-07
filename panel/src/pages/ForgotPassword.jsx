import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errMsg } from "../api/client";
import { Notice, Spinner, Field } from "../components/ui";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    if (loading) return;
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const res = await api.post("/v1/auth/forgot-password", { email });
      const msg =
        (res.data && res.data.message) ||
        "If that email exists, a reset link has been sent.";
      setSuccess(msg);
    } catch (err) {
      setError(errMsg(err, "Something went wrong. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-dot">✦</span>
          <span>ChatBot</span>
        </div>
        <div className="auth-sub">Reset your password</div>

        <Notice type="success" onClose={() => setSuccess("")}>
          {success}
        </Notice>
        <Notice type="error" onClose={() => setError("")}>
          {error}
        </Notice>

        <form onSubmit={onSubmit}>
          <Field label="Email">
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </Field>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={loading}
          >
            {loading ? <Spinner /> : "Send reset link"}
          </button>
        </form>

        <div className="auth-foot">
          <Link to="/login">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
