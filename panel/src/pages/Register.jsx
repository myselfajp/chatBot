import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errMsg } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Notice, Spinner, Field } from "../components/ui";

const PASSWORD_HINT =
  "At least 8 characters, including one uppercase, one lowercase, and one digit.";

export default function Register() {
  const { user, register, login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone_number: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState("");

  useEffect(() => {
    if (user) navigate("/");
  }, [user, navigate]);

  const onChange = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setCreated("");
    setLoading(true);
    try {
      await register({
        full_name: form.full_name,
        email: form.email,
        phone_number: form.phone_number,
        password: form.password,
      });

      // Account created — try to sign the user straight in.
      try {
        const res = await login(form.email, form.password);
        if (res.status === "authenticated") {
          navigate("/", { replace: true });
          return;
        }
        // otp_required (or anything else) -> ask them to sign in manually.
        setCreated(
          "Your account was created. Please sign in to continue."
        );
      } catch {
        setCreated(
          "Your account was created. Please sign in to continue."
        );
      }
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-dot">✦</span> ChatBot
        </div>
        <div className="auth-sub">Create your account</div>

        <Notice type="error" onClose={() => setError("")}>
          {error}
        </Notice>
        <Notice type="success">{created}</Notice>

        {created ? (
          <div className="text-center mt-2">
            <Link to="/login">Go to sign in</Link>
          </div>
        ) : (
          <form onSubmit={onSubmit}>
            <Field label="Full name">
              <input
                className="input"
                type="text"
                value={form.full_name}
                onChange={onChange("full_name")}
                placeholder="Jane Doe"
                autoComplete="name"
                required
              />
            </Field>

            <Field label="Email">
              <input
                className="input"
                type="email"
                value={form.email}
                onChange={onChange("email")}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </Field>

            <Field label="Phone number">
              <input
                className="input"
                type="tel"
                value={form.phone_number}
                onChange={onChange("phone_number")}
                placeholder="+1 555 123 4567"
                autoComplete="tel"
                required
              />
            </Field>

            <Field label="Password" hint={PASSWORD_HINT}>
              <input
                className="input"
                type="password"
                value={form.password}
                onChange={onChange("password")}
                placeholder="••••••••"
                autoComplete="new-password"
                required
              />
            </Field>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading}
            >
              {loading ? <Spinner /> : "Create account"}
            </button>
          </form>
        )}

        <div className="auth-foot">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
