import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "../ui";
import { useAuth } from "../../hooks/useAuth";

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isWorkspace = location.pathname === "/workspace";
  const isProfile = location.pathname === "/profile";

  return (
    <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-gray-900">Canon</h1>
        <nav className="flex gap-2">
          <button
            onClick={() => navigate("/workspace")}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              isWorkspace
                ? "bg-blue-100 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Workspace
          </button>
          <button
            onClick={() => navigate("/profile")}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              isProfile
                ? "bg-blue-100 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Profile
          </button>
        </nav>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={handleLogout}>
          Logout
        </Button>
      </div>
    </div>
  );
};

