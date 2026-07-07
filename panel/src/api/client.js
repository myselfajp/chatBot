import axios from "axios";

// Backend base URL. Override with VITE_API_BASE in panel/.env
export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const TOKEN_KEY = "chatbot_panel_token";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      // Avoid redirect loops on the auth pages themselves.
      const p = window.location.pathname;
      if (!p.startsWith("/login") && !p.startsWith("/register")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

// Normalize an axios error into a human-readable string.
export function errMsg(err, fallback = "Something went wrong") {
  const d = err && err.response && err.response.data;
  if (d) {
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail) && d.detail.length) {
      return d.detail.map((e) => e.msg || e.detail || "").join(", ");
    }
    if (typeof d.message === "string") return d.message;
  }
  if (err && err.message) return err.message;
  return fallback;
}

export default api;
