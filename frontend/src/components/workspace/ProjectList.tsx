import React, { useState } from "react";
import { ChevronRight, ChevronDown, Folder, Plus, FileText, Trash2, X } from "lucide-react";
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
    <div className="flex flex-col h-full bg-gradient-to-b from-white to-gray-50/30">
      <div className="p-4 border-b border-gray-200 bg-gradient-to-br from-gray-50 to-white shadow-sm">
        <Button
          onClick={() => setShowCreateProjectForm(!showCreateProjectForm)}
          className="w-full flex justify-center items-center gap-2"
          size="sm"
          variant="default"
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          {showCreateProjectForm ? "Cancel" : "New Project"}
        </Button>
        {showCreateProjectForm && (
          <div className="mt-3 space-y-2 transition-all duration-200">
            <Input
              placeholder="Project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCreateProject()}
              className="text-sm"
              autoFocus
            />
            <Button 
              onClick={handleCreateProject} 
              className="w-full" 
              size="sm" 
              disabled={createProject.isPending}
            >
              {createProject.isPending ? "Creating..." : "Create Project"}
            </Button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto">
        {projects && projects.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center shadow-sm">
              <Folder className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-sm font-semibold text-gray-700 mb-1">No projects yet</p>
            <p className="text-xs text-gray-500">Create your first project to get started</p>
          </div>
        ) : (
          <div className="py-1">
            {projects?.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              const isSelected = selectedProjectId === project.id;
              const documentCount = project.documents?.length || 0;
              return (
                <div key={project.id} className="group">
                  <div
                    onClick={() => {
                      onSelectProject(project);
                      onToggleProject(project.id);
                    }}
                    className={`relative px-4 py-3 cursor-pointer transition-all duration-200 rounded-r-lg ${
                      isSelected 
                        ? "bg-gradient-to-r from-blue-50 to-blue-100/50 border-l-4 border-blue-600 text-blue-900 shadow-sm" 
                        : "hover:bg-gray-50 text-gray-700 hover:shadow-sm"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <div className="flex-shrink-0 transition-transform duration-200">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-500" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                          )}
                        </div>
                        <Folder className={`w-4 h-4 flex-shrink-0 ${isSelected ? "text-blue-600" : "text-gray-500"}`} />
                        <div className="font-medium text-sm truncate flex-1">{project.name}</div>
                        {documentCount > 0 && (
                          <span className={`text-xs px-2 py-1 rounded-full flex-shrink-0 font-medium ${
                            isSelected 
                              ? "bg-blue-200 text-blue-800 shadow-sm" 
                              : "bg-gray-200 text-gray-700"
                          }`}>
                            {documentCount}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={(e) => handleDeleteProjectClick(e, project.id)}
                        className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 flex-shrink-0 hover:scale-110"
                        title="Delete project"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="transition-all duration-200">
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
                    </div>
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
    return (
      <div className="bg-gray-50/50 border-l-2 border-gray-100 px-3 py-4">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className="w-3.5 h-3.5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
          Loading documents...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-gray-50/80 to-white border-l-2 border-gray-200">
      <div className="px-4 py-3 border-b border-gray-200/60">
        <Button
          onClick={() => onShowCreateFormChange(!showCreateForm)}
          className="w-full flex justify-center items-center gap-1.5 h-7 text-xs"
          size="sm"
          variant="ghost"
        >
          {showCreateForm ? (
            <>
              <X className="w-3 h-3 flex-shrink-0" />
              Cancel
            </>
          ) : (
            <>
              <Plus className="w-3 h-3 flex-shrink-0" />
              New Document
            </>
          )}
        </Button>
        {showCreateForm && (
          <div className="mt-2 space-y-2 transition-all duration-200">
            <Input
              placeholder="Document name"
              value={newDocumentName}
              onChange={(e) => onNewDocumentNameChange(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && onCreateDocument()}
              className="text-sm h-8"
              autoFocus
            />
            <Button 
              onClick={onCreateDocument} 
              className="w-full h-7 text-xs" 
              size="sm" 
              disabled={createDocumentPending}
            >
              {createDocumentPending ? "Creating..." : "Create Document"}
            </Button>
          </div>
        )}
      </div>
      {documents && documents.length === 0 ? (
        <div className="px-4 py-6 text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center shadow-sm">
            <FileText className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-xs font-medium text-gray-600">No documents yet</p>
        </div>
      ) : (
        <div className="py-1">
          {documents?.map((document) => {
            const isSelected = selectedDocumentId === document.id;
            const contentLength = document.content?.length || 0;
            return (
              <div
                key={document.id}
                onClick={() => onSelectDocument(document)}
                className={`group relative px-4 py-3 pl-12 cursor-pointer transition-all duration-200 rounded-r-lg ${
                  isSelected 
                    ? "bg-gradient-to-r from-blue-50 to-blue-100/50 border-l-4 border-blue-500 text-blue-900 shadow-sm" 
                    : "hover:bg-gray-100/80 text-gray-700 hover:shadow-sm"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${
                      isSelected ? "text-blue-600" : "text-gray-400"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className={`font-medium text-sm truncate ${
                        isSelected ? "text-blue-900" : "text-gray-800"
                      }`}>
                        {document.name}
                      </div>
                      <div className={`text-xs mt-0.5 ${
                        isSelected ? "text-blue-600" : "text-gray-500"
                      }`}>
                        {contentLength > 0 
                          ? `${contentLength.toLocaleString()} ${contentLength === 1 ? 'character' : 'characters'}`
                          : "Empty document"
                        }
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={(e) => onDeleteDocument(e, projectId, document.id)}
                    className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 flex-shrink-0 hover:scale-110"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

