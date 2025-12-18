import React, { useState } from "react";
import { Module } from "../types";
import { ModuleList } from "../components/ModuleList";
import { DocumentView } from "../components/DocumentView";
import { ChatPanel } from "../components/ChatPanel";
import { useQueryClient } from "@tanstack/react-query";

export const WorkspaceLayout: React.FC = () => {
  const [selectedModule, setSelectedModule] = useState<Module | null>(null);
  const [chatId, setChatId] = useState<number | null>(null);
  const queryClient = useQueryClient();

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
    <div className="flex h-screen">
      <div className="w-64 flex-shrink-0">
        <ModuleList
          selectedModuleId={selectedModule?.id || null}
          onSelectModule={handleModuleSelected}
        />
      </div>
      <div className="flex-1 flex-shrink-0">
        <DocumentView module={selectedModule} />
      </div>
      <div className="w-80 flex-shrink-0">
        <ChatPanel
          module={selectedModule}
          chatId={chatId}
          onChatCreated={setChatId}
          onModuleUpdated={handleModuleUpdated}
        />
      </div>
    </div>
  );
};



