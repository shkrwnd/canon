import React, { useState, useEffect } from "react";
import { Module } from "../types";
import { WorkspaceLayout } from "../layouts/WorkspaceLayout";
import { LeftSidebar, RightSidebar, DocumentView } from "../components/workspace";
import { useQueryClient } from "@tanstack/react-query";
import { useModules } from "../hooks/useModules";

export const WorkspacePage: React.FC = () => {
  const [selectedModule, setSelectedModule] = useState<Module | null>(null);
  const [chatId, setChatId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const { data: modules } = useModules();

  // Listen for module selection from search
  useEffect(() => {
    const handleModuleSelect = (event: CustomEvent<{ moduleId: number }>) => {
      const module = modules?.find((m) => m.id === event.detail.moduleId);
      if (module) {
        setSelectedModule(module);
      }
    };

    window.addEventListener("selectModule", handleModuleSelect as EventListener);
    return () => {
      window.removeEventListener("selectModule", handleModuleSelect as EventListener);
    };
  }, [modules]);

  const handleModuleSelected = (module: Module | null) => {
    setSelectedModule(module);
    // Reset chatId when module changes - each module should have its own chat
    setChatId(null);
  };

  const handleModuleUpdated = (module: Module) => {
    // Update the selected module
    setSelectedModule(module);
    // Invalidate queries to refresh data
    queryClient.invalidateQueries({ queryKey: ["modules"] });
    queryClient.invalidateQueries({ queryKey: ["module", module.id] });
  };

  return (
    <WorkspaceLayout>
      <LeftSidebar
        selectedModuleId={selectedModule?.id || null}
        onSelectModule={handleModuleSelected}
      />
      <div className="flex-1 flex-shrink-0">
        <DocumentView module={selectedModule} />
      </div>
      <RightSidebar
        module={selectedModule}
        chatId={chatId}
        onChatCreated={setChatId}
        onModuleUpdated={handleModuleUpdated}
      />
    </WorkspaceLayout>
  );
};



