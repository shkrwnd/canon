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
      <div className="text-center mb-8">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Canon</h1>
        <p className="text-base text-gray-600">Living Documents Editor</p>
        <p className="text-sm text-gray-500 mt-2">AI-powered document management</p>
      </div>
      <AuthForm mode={mode} onSubmit={handleSubmit} onToggleMode={() => setMode(mode === "login" ? "register" : "login")} />
    </AuthLayout>
  );
};



