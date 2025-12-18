import React, { ReactNode } from "react";
import { Header } from "../components/shared";

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  );
};



