import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errMsg } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Notice, Spinner } from "../components/ui";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState(null);
  const [otpMsg, setOtpMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result.status === "authenticated") {
        navigate("/", { replace: true });
      } else if (result.status === "otp_required") {
        setChallenge(result.challenge_id);
        setOtpMsg(
          [result.message, result.destination].filter(Boolean).join(" ")
        );
      }
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  }

  async function onVerify(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login(email, password, {
        code,
        challenge_id: challenge,
      });
      if (result.status === "authenticated") {
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-dot">✦</span> ChatBot
        </div>
        <div className="auth-sub">Sign in to your account</div>

        <Notice type="error" onClose={() => setError("")}>
          {error}
        </Notice>

        {challenge ? (
          <form onSubmit={onVerify}>
            <Notice type="info">{otpMsg}</Notice>
            <div className="field">
              <label className="label">Verification code</label>
              <input
                className="input"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoFocus
              />
            </div>
            <button
              className="btn btn-primary btn-block"
              type="submit"
              disabled={loading}
            >
              {loading ? <Spinner /> : "Verify"}
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmit}>
            <div className="field">
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
              />
            </div>
            <div className="field">
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button
              className="btn btn-primary btn-block"
              type="submit"
              disabled={loading}
            >
              {loading ? <Spinner /> : "Sign in"}
            </button>
          </form>
        )}

        <div className="auth-foot">
          <Link to="/forgot-password">Forgot password?</Link>
          <div className="mt-1">
            Don't have an account? <Link to="/register">Create one</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
