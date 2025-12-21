import React, { useState, useEffect } from "react";
import { Project, Document } from "../types";
import { WorkspaceLayout } from "../layouts/WorkspaceLayout";
import { LeftSidebar, RightSidebar, DocumentView } from "../components/workspace";
import { useQueryClient } from "@tanstack/react-query";
import { useProjects } from "../hooks/useProjects";
import { useDocuments } from "../hooks/useDocuments";
import { useChatByProject } from "../hooks/useChat";

export const WorkspacePage: React.FC = () => {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const queryClient = useQueryClient();
  const { data: projects } = useProjects();
  const { data: documents } = useDocuments(selectedProject?.id || null);
  const { data: chat } = useChatByProject(selectedProject?.id || null);

  // Listen for project and document selection from search
  useEffect(() => {
    const handleProjectSelect = (event: CustomEvent<{ projectId: number }>) => {
      const project = projects?.find((p) => p.id === event.detail.projectId);
      if (project) {
        setSelectedProject(project);
      }
    };

    const handleDocumentSelect = (event: CustomEvent<{ projectId: number; documentId: number }>) => {
      const project = projects?.find((p) => p.id === event.detail.projectId);
      if (project) {
        setSelectedProject(project);
        // We'll need to fetch documents for this project first
        // For now, just select the project and let the user select the document
      }
    };

    window.addEventListener("selectProject", handleProjectSelect as EventListener);
    window.addEventListener("selectDocument", handleDocumentSelect as EventListener);
    return () => {
      window.removeEventListener("selectProject", handleProjectSelect as EventListener);
      window.removeEventListener("selectDocument", handleDocumentSelect as EventListener);
    };
  }, [projects]);

  const handleProjectSelected = (project: Project | null) => {
    setSelectedProject(project);
    // Reset document when project changes
    // Chat will be automatically loaded via useChatByProject hook
    setSelectedDocument(null);
  };

  const handleDocumentSelected = (document: Document | null) => {
    setSelectedDocument(document);
    // Keep the same chat when switching documents within the same project
    // Chat is project-level, not document-level
  };

  const handleDocumentUpdated = (document: Document) => {
    // Update the selected document
    setSelectedDocument(document);
    // Invalidate queries to refresh data
    if (selectedProject?.id) {
      queryClient.invalidateQueries({ queryKey: ["documents", selectedProject.id] });
      queryClient.invalidateQueries({ queryKey: ["document", selectedProject.id, document.id] });
    }
  };

  const handleCreateDocumentClick = () => {
    // This will be handled by the ProjectList component
    // We can trigger focus on the document input if needed
  };

  return (
    <WorkspaceLayout>
      <LeftSidebar
        selectedProjectId={selectedProject?.id || null}
        selectedDocumentId={selectedDocument?.id || null}
        onSelectProject={handleProjectSelected}
        onSelectDocument={handleDocumentSelected}
      />
      <div className="flex-1 flex-shrink-0">
        <DocumentView 
          document={selectedDocument} 
          projectId={selectedProject?.id || null}
          onCreateDocument={handleCreateDocumentClick}
          hasDocuments={(documents?.length || 0) > 0}
        />
      </div>
      <RightSidebar
        project={selectedProject}
        document={selectedDocument}
        chatId={chat?.id || null}
        onChatCreated={(newChatId) => {
          // Invalidate chat query to refetch
          queryClient.invalidateQueries({ queryKey: ["chat", "project", selectedProject?.id] });
        }}
        onDocumentUpdated={handleDocumentUpdated}
      />
    </WorkspaceLayout>
  );
};



