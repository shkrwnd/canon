import React, { useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./components/ui";
import { AppRoutes } from "./routes";
import { queryClient } from "./config/queryClient";
import { initGoogleTag } from "./analytics/googleTag";
import "./index.css";

const App: React.FC = () => {
  useEffect(() => {
    initGoogleTag();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;



