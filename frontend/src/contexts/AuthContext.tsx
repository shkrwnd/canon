import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { isAuthenticated, getAuthToken, removeAuthToken } from "../helpers/authHelpers";
import { login as loginService, register as registerService } from "../services/authService";
import { UserLogin, UserRegister } from "../types";

interface AuthContextType {
  authenticated: boolean;
  loading: boolean;
  login: (data: UserLogin) => Promise<void>;
  register: (data: UserRegister) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated on mount
    setAuthenticated(isAuthenticated());
    setLoading(false);
  }, []);

  const login = async (data: UserLogin) => {
    await loginService(data);
    setAuthenticated(true);
  };

  const register = async (data: UserRegister) => {
    await registerService(data);
    setAuthenticated(true);
  };

  const logout = () => {
    removeAuthToken();
    setAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ authenticated, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};



