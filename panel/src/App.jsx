import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import BotEditor from "./pages/BotEditor";
import AdminUsers from "./pages/admin/Users";
import AdminBots from "./pages/admin/Bots";

export default function App() {
  return (
    <Routes>
      {/* Public auth routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Authenticated routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bots/:id"
        element={
          <ProtectedRoute>
            <BotEditor />
          </ProtectedRoute>
        }
      />

      {/* Admin routes */}
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute adminOnly>
            <AdminUsers />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/bots"
        element={
          <ProtectedRoute adminOnly>
            <AdminBots />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
