import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LoginPage } from "../pages/LoginPage";
import { WorkspacePage } from "../pages/WorkspacePage";
import { ProtectedRoute } from "./ProtectedRoute";

export const AppRoutes: React.FC = () => {
  const { authenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={authenticated ? <Navigate to="/workspace" replace /> : <LoginPage />}
      />
      <Route
        path="/workspace"
        element={
          <ProtectedRoute>
            <WorkspacePage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/workspace" replace />} />
    </Routes>
  );
};

export { ProtectedRoute } from "./ProtectedRoute";

