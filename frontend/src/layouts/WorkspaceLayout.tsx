import React, { ReactNode } from "react";

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen">
      {children}
    </div>
  );
};



