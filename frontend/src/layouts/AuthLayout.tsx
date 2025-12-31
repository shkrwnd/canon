import React, { ReactNode } from "react";

interface AuthLayoutProps {
  children: ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-large border-2 border-gray-100">
        {children}
      </div>
    </div>
  );
};





