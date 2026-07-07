import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { TOKEN_KEY } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/v1/me");
      setUser(data);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  /**
   * Attempt login. Returns:
   *   { status: "authenticated" }        -> logged in, user set
   *   { status: "otp_required", ... }    -> caller must collect OTP and retry
   */
  const login = useCallback(async (email, password, otp) => {
    const body = { email, password };
    if (otp) {
      body.otp_code = otp.code;
      body.otp_challenge_id = otp.challenge_id;
    }
    const { data } = await api.post("/v1/auth/login", body);
    if (data.status === "otp_required") {
      return data;
    }
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
    return { status: "authenticated", user: data.user };
  }, []);

  const register = useCallback(async (payload) => {
    const { data } = await api.post("/v1/auth/register", payload);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    window.location.href = "/login";
  }, []);

  const value = {
    user,
    loading,
    isAdmin: user?.role === "admin",
    login,
    register,
    logout,
    refresh: loadMe,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
