import React, { useState } from "react";
import { ChevronRight, ChevronDown, Folder, Plus } from "lucide-react";
import { Project, Document } from "../../types";
import { useProjects, useCreateProject, useDeleteProject } from "../../hooks/useProjects";
import { useDocuments, useCreateDocument, useDeleteDocument } from "../../hooks/useDocuments";
import { Button, Input, Dialog, useToast } from "../ui";

interface ProjectListProps {
  selectedProjectId: number | null;
  selectedDocumentId: number | null;
  onSelectProject: (project: Project | null) => void;
  onSelectDocument: (document: Document | null) => void;
  expandedProjects: Set<number>;
  onToggleProject: (projectId: number) => void;
}

export const ProjectList: React.FC<ProjectListProps> = ({
  selectedProjectId,
  selectedDocumentId,
  onSelectProject,
  onSelectDocument,
  expandedProjects,
  onToggleProject,
}) => {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const { showToast } = useToast();
  const [showCreateProjectForm, setShowCreateProjectForm] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [deleteProjectDialogOpen, setDeleteProjectDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<number | null>(null);
  const [showCreateDocumentForm, setShowCreateDocumentForm] = useState<number | null>(null);
  const [newDocumentName, setNewDocumentName] = useState("");
  const [deleteDocumentDialogOpen, setDeleteDocumentDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<{ projectId: number; documentId: number } | null>(null);

  const createDocument = useCreateDocument();
  const deleteDocument = useDeleteDocument();

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      showToast("Project name is required", "error");
      return;
    }

    try {
      const project = await createProject.mutateAsync({
        name: newProjectName.trim(),
        description: "",
      });
      setNewProjectName("");
      setShowCreateProjectForm(false);
      onSelectProject(project);
      onToggleProject(project.id);
      showToast("Project created successfully", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to create project", "error");
    }
  };

  const handleCreateDocument = async (projectId: number) => {
    if (!newDocumentName.trim()) {
      showToast("Document name is required", "error");
      return;
    }

    try {
      const document = await createDocument.mutateAsync({
        projectId,
        data: {
          name: newDocumentName.trim(),
          standing_instruction: "",
          content: "",
          project_id: projectId,
        },
      });
      setNewDocumentName("");
      setShowCreateDocumentForm(null);
      onSelectDocument(document);
      showToast("Document created successfully", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to create document", "error");
    }
  };

  const handleDeleteProjectClick = (e: React.MouseEvent, projectId: number) => {
    e.stopPropagation();
    setProjectToDelete(projectId);
    setDeleteProjectDialogOpen(true);
  };

  const handleDeleteProjectConfirm = async () => {
    if (projectToDelete === null) return;

    try {
      await deleteProject.mutateAsync(projectToDelete);
      if (selectedProjectId === projectToDelete) {
        onSelectProject(null);
        onSelectDocument(null);
      }
      showToast("Project deleted successfully", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to delete project", "error");
    } finally {
      setDeleteProjectDialogOpen(false);
      setProjectToDelete(null);
    }
  };

  const handleDeleteDocumentClick = (e: React.MouseEvent, projectId: number, documentId: number) => {
    e.stopPropagation();
    setDocumentToDelete({ projectId, documentId });
    setDeleteDocumentDialogOpen(true);
  };

  const handleDeleteDocumentConfirm = async () => {
    if (!documentToDelete) return;

    try {
      await deleteDocument.mutateAsync({
        projectId: documentToDelete.projectId,
        documentId: documentToDelete.documentId,
      });
      if (selectedDocumentId === documentToDelete.documentId) {
        onSelectDocument(null);
      }
      showToast("Document deleted successfully", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to delete document", "error");
    } finally {
      setDeleteDocumentDialogOpen(false);
      setDocumentToDelete(null);
    }
  };

  if (isLoading) {
    return <div className="p-4">Loading projects...</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <Button
          onClick={() => setShowCreateProjectForm(!showCreateProjectForm)}
          className="w-full"
          size="sm"
        >
          {showCreateProjectForm ? "Cancel" : "+ New Project"}
        </Button>
        {showCreateProjectForm && (
          <div className="mt-2 space-y-2">
            <Input
              placeholder="Project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCreateProject()}
            />
            <Button onClick={handleCreateProject} className="w-full" size="sm" disabled={createProject.isPending}>
              Create
            </Button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto">
        {projects && projects.length === 0 ? (
          <div className="p-4 text-sm text-gray-500 text-center">
            No projects yet. Create one to get started.
          </div>
        ) : (
          <div className="divide-y">
            {projects?.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              const isSelected = selectedProjectId === project.id;
              return (
                <div key={project.id}>
                  <div
                    onClick={() => {
                      onSelectProject(project);
                      onToggleProject(project.id);
                    }}
                    className={`p-3 cursor-pointer hover:bg-gray-50 ${
                      isSelected ? "bg-blue-50 border-l-4 border-blue-600" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        )}
                        <Folder className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        <div className="font-medium text-sm truncate">{project.name}</div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteProjectClick(e, project.id)}
                        className="ml-2 text-red-500 hover:text-red-700 text-xs flex-shrink-0"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <ProjectDocuments
                      projectId={project.id}
                      selectedDocumentId={selectedDocumentId}
                      onSelectDocument={onSelectDocument}
                      showCreateForm={showCreateDocumentForm === project.id}
                      onShowCreateFormChange={(show) => setShowCreateDocumentForm(show ? project.id : null)}
                      newDocumentName={newDocumentName}
                      onNewDocumentNameChange={setNewDocumentName}
                      onCreateDocument={() => handleCreateDocument(project.id)}
                      onDeleteDocument={handleDeleteDocumentClick}
                      createDocumentPending={createDocument.isPending}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <Dialog
        open={deleteProjectDialogOpen}
        onClose={() => {
          setDeleteProjectDialogOpen(false);
          setProjectToDelete(null);
        }}
        title="Delete Project"
        description="Are you sure you want to delete this project? This will also delete all documents within it. This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={handleDeleteProjectConfirm}
      />

      <Dialog
        open={deleteDocumentDialogOpen}
        onClose={() => {
          setDeleteDocumentDialogOpen(false);
          setDocumentToDelete(null);
        }}
        title="Delete Document"
        description="Are you sure you want to delete this document? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={handleDeleteDocumentConfirm}
      />
    </div>
  );
};

interface ProjectDocumentsProps {
  projectId: number;
  selectedDocumentId: number | null;
  onSelectDocument: (document: Document | null) => void;
  showCreateForm: boolean;
  onShowCreateFormChange: (show: boolean) => void;
  newDocumentName: string;
  onNewDocumentNameChange: (name: string) => void;
  onCreateDocument: () => void;
  onDeleteDocument: (e: React.MouseEvent, projectId: number, documentId: number) => void;
  createDocumentPending: boolean;
}

const ProjectDocuments: React.FC<ProjectDocumentsProps> = ({
  projectId,
  selectedDocumentId,
  onSelectDocument,
  showCreateForm,
  onShowCreateFormChange,
  newDocumentName,
  onNewDocumentNameChange,
  onCreateDocument,
  onDeleteDocument,
  createDocumentPending,
}) => {
  const { data: documents, isLoading } = useDocuments(projectId);

  if (isLoading) {
    return <div className="p-2 pl-8 text-xs text-gray-500">Loading documents...</div>;
  }

  return (
    <div className="bg-gray-50">
      <div className="p-2 pl-8 border-b">
        <Button
          onClick={() => onShowCreateFormChange(!showCreateForm)}
          className="w-full"
          size="sm"
          variant="ghost"
        >
          {showCreateForm ? "Cancel" : <><Plus className="w-3 h-3 mr-1" /> New Document</>}
        </Button>
        {showCreateForm && (
          <div className="mt-2 space-y-2">
            <Input
              placeholder="Document name"
              value={newDocumentName}
              onChange={(e) => onNewDocumentNameChange(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && onCreateDocument()}
              className="text-sm py-1.5"
            />
            <Button onClick={onCreateDocument} className="w-full" size="sm" disabled={createDocumentPending}>
              Create
            </Button>
          </div>
        )}
      </div>
      {documents && documents.length === 0 ? (
        <div className="p-2 pl-8 text-xs text-gray-500">No documents yet.</div>
      ) : (
        <div className="divide-y divide-gray-200">
          {documents?.map((document) => (
            <div
              key={document.id}
              onClick={() => onSelectDocument(document)}
              className={`p-3 pl-12 cursor-pointer hover:bg-gray-100 ${
                selectedDocumentId === document.id ? "bg-blue-100 border-l-4 border-blue-600" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{document.name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {document.content ? `${document.content.length} chars` : "Empty"}
                  </div>
                </div>
                <button
                  onClick={(e) => onDeleteDocument(e, projectId, document.id)}
                  className="ml-2 text-red-500 hover:text-red-700 text-xs"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

