import React, { useState } from "react";
import { ResizablePanel } from "./ResizablePanel";
import { ProjectList } from "./ProjectList";
import { Project, Document } from "../../types";

interface LeftSidebarProps {
  selectedProjectId: number | null;
  selectedDocumentId: number | null;
  onSelectProject: (project: Project | null) => void;
  onSelectDocument: (document: Document | null) => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  selectedProjectId,
  selectedDocumentId,
  onSelectProject,
  onSelectDocument,
}) => {
  const [expandedProjects, setExpandedProjects] = useState<Set<number>>(new Set());

  const handleToggleProject = (projectId: number) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  return (
    <ResizablePanel side="left" initialWidth={256} minWidth={200} maxWidth={600}>
      <ProjectList
        selectedProjectId={selectedProjectId}
        selectedDocumentId={selectedDocumentId}
        onSelectProject={onSelectProject}
        onSelectDocument={onSelectDocument}
        expandedProjects={expandedProjects}
        onToggleProject={handleToggleProject}
      />
    </ResizablePanel>
  );
};

