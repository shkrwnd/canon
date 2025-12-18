import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthLayout } from "../layouts/AuthLayout";
import { AuthForm } from "../components/auth";
import { useAuth } from "../hooks/useAuth";
import { UserLogin, UserRegister } from "../types";

export const LoginPage: React.FC = () => {
  const [mode, setMode] = useState<"login" | "register">("login");
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (data: UserLogin | UserRegister) => {
    if (mode === "login") {
      await login(data as UserLogin);
    } else {
      await register(data as UserRegister);
    }
    navigate("/workspace");
  };

  return (
    <AuthLayout>
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Canon</h1>
        <p className="text-sm text-gray-600 mt-2">Living Documents Editor</p>
      </div>
      <AuthForm mode={mode} onSubmit={handleSubmit} onToggleMode={() => setMode(mode === "login" ? "register" : "login")} />
    </AuthLayout>
  );
};



