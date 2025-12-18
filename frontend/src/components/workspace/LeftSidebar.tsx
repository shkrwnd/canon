import React from "react";
import { ResizablePanel } from "./ResizablePanel";
import { ModuleList } from "./ModuleList";
import { Module } from "../../types";

interface LeftSidebarProps {
  selectedModuleId: number | null;
  onSelectModule: (module: Module | null) => void;
  showCreateForm?: boolean;
  onShowCreateFormChange?: (show: boolean) => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  selectedModuleId,
  onSelectModule,
  showCreateForm,
  onShowCreateFormChange,
}) => {
  return (
    <ResizablePanel side="left" initialWidth={256} minWidth={200} maxWidth={600}>
      <ModuleList
        selectedModuleId={selectedModuleId}
        onSelectModule={onSelectModule}
        showCreateForm={showCreateForm}
        onShowCreateFormChange={onShowCreateFormChange}
      />
    </ResizablePanel>
  );
};

