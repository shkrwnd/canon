import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { isAuthenticated, removeAuthToken, getEmailFromToken } from "../utils/auth.utils";
import { login as loginService, register as registerService } from "../services/authService";
import { UserLogin, UserRegister } from "../types";

interface AuthContextType {
  authenticated: boolean;
  loading: boolean;
  userEmail: string | null;
  login: (data: UserLogin) => Promise<void>;
  register: (data: UserRegister) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    setAuthenticated(isAuthenticated());
    setUserEmail(getEmailFromToken());
    setLoading(false);
  }, []);

  const login = async (data: UserLogin) => {
    await loginService(data);
    setAuthenticated(true);
    setUserEmail(getEmailFromToken());
  };

  const register = async (data: UserRegister) => {
    await registerService(data);
    setAuthenticated(true);
    setUserEmail(getEmailFromToken());
  };

  const logout = () => {
    removeAuthToken();
    setAuthenticated(false);
    setUserEmail(null);
  };

  return (
    <AuthContext.Provider value={{ authenticated, loading, userEmail, login, register, logout }}>
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



