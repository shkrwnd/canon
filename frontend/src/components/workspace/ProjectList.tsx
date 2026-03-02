import React, { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Plus,
  Check,
  FileText,
  Trash2,
  X,
  FolderOpen,
} from "lucide-react";
import { Project, Document } from "../../types";
import { useProjects, useCreateProject, useDeleteProject } from "../../hooks/useProjects";
import { useDocuments, useCreateDocument, useDeleteDocument } from "../../hooks/useDocuments";
import { Dialog, useToast } from "../ui";

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
  const [documentToDelete, setDocumentToDelete] = useState<{
    projectId: number;
    documentId: number;
  } | null>(null);

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
      showToast("Project created", "success");
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
      showToast("Document created", "success");
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
      showToast("Project deleted", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to delete project", "error");
    } finally {
      setDeleteProjectDialogOpen(false);
      setProjectToDelete(null);
    }
  };

  const handleDeleteDocumentClick = (
    e: React.MouseEvent,
    projectId: number,
    documentId: number
  ) => {
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
      showToast("Document deleted", "success");
    } catch (error: any) {
      showToast(error.response?.data?.detail || "Failed to delete document", "error");
    } finally {
      setDeleteDocumentDialogOpen(false);
      setDocumentToDelete(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
        <div className="p-5 flex items-center gap-1.5">
          {[0, 0.15, 0.3].map((delay, i) => (
            <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-pulse" style={{ animationDelay: `${delay}s` }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
      {/* Sidebar header */}
      <div className="px-4 pt-5 pb-4 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.1em]">
            Projects
          </span>
          <button
            onClick={() => setShowCreateProjectForm(!showCreateProjectForm)}
            className="w-5 h-5 rounded flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
            title="New project"
          >
            {showCreateProjectForm ? (
              <X className="w-3 h-3" />
            ) : (
              <Plus className="w-3 h-3" />
            )}
          </button>
        </div>

        {showCreateProjectForm && (
          <div className="mt-3 space-y-2">
            <input
              type="text"
              placeholder="Project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCreateProject()}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-shadow"
              autoFocus
            />
            <button
              onClick={handleCreateProject}
              disabled={createProject.isPending}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              {createProject.isPending ? "Creating..." : "Create Project"}
            </button>
          </div>
        )}
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-auto py-2">
        {projects && projects.length === 0 ? (
          <div className="px-4 py-10 text-center">
            <div className="w-9 h-9 mx-auto mb-3 rounded-xl bg-slate-200 flex items-center justify-center">
              <FolderOpen className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-xs font-semibold text-slate-500 mb-1">No projects yet</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Click + above to get started
            </p>
          </div>
        ) : (
          <div>
            {projects?.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              const isSelected = selectedProjectId === project.id;
              const documentCount = project.documents?.length || 0;

              return (
                <div key={project.id}>
                  {/* Project row */}
                  <div
                    onClick={() => {
                      onSelectProject(project);
                      onToggleProject(project.id);
                    }}
                    className={`group relative flex items-center gap-2 px-3 py-2.5 mx-2 rounded-lg cursor-pointer transition-all duration-150 ${
                      isSelected
                        ? "bg-white shadow-sm text-slate-900"
                        : "text-slate-600 hover:bg-slate-200/70 hover:text-slate-800"
                    }`}
                  >
                    {/* Active indicator */}
                    {isSelected && (
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-blue-500 rounded-full" />
                    )}

                    <span className={`flex-shrink-0 transition-transform duration-150 ${isSelected ? "text-slate-500 ml-2" : "text-slate-400 ml-2"}`}>
                      {isExpanded ? (
                        <ChevronDown className="w-3 h-3" />
                      ) : (
                        <ChevronRight className="w-3 h-3" />
                      )}
                    </span>

                    <FolderOpen
                      className={`w-3.5 h-3.5 flex-shrink-0 ${
                        isSelected ? "text-blue-600" : "text-slate-400"
                      }`}
                    />

                    <span className={`text-sm truncate flex-1 leading-none py-0.5 min-w-0 ${isSelected ? "font-semibold" : "font-medium"}`}>
                      {project.name}
                    </span>

                    {documentCount > 0 && (
                      <span className="text-[11px] text-slate-400 tabular-nums font-medium flex-shrink-0">
                        {documentCount}
                      </span>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!expandedProjects.has(project.id)) onToggleProject(project.id);
                        setShowCreateDocumentForm(showCreateDocumentForm === project.id ? null : project.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700 flex-shrink-0"
                      title="New document"
                    >
                      <Plus className="w-3 h-3" />
                    </button>

                    <button
                      onClick={(e) => handleDeleteProjectClick(e, project.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 flex-shrink-0"
                      title="Delete project"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Documents */}
                  {isExpanded && (
                    <ProjectDocuments
                      projectId={project.id}
                      selectedDocumentId={selectedDocumentId}
                      onSelectDocument={onSelectDocument}
                      showCreateForm={showCreateDocumentForm === project.id}
                      onShowCreateFormChange={(show) =>
                        setShowCreateDocumentForm(show ? project.id : null)
                      }
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
  onDeleteDocument: (
    e: React.MouseEvent,
    projectId: number,
    documentId: number
  ) => void;
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
      <div className="pl-10 pr-3 py-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <div className="w-1 h-1 rounded-full bg-slate-300 animate-pulse" />
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="border-l-2 border-slate-200 ml-6 mt-0.5 mb-1">
      {showCreateForm && (
        <div className="px-2 pt-1 pb-1.5">
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              placeholder="Document name"
              value={newDocumentName}
              onChange={(e) => onNewDocumentNameChange(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && onCreateDocument()}
              className="flex-1 bg-white border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 min-w-0"
              autoFocus
            />
            <button
              onClick={onCreateDocument}
              disabled={createDocumentPending}
              className="p-1 rounded hover:bg-green-100 text-slate-400 hover:text-green-600 flex-shrink-0 disabled:opacity-50"
              title="Create"
            >
              <Check className="w-3 h-3" />
            </button>
            <button
              onClick={() => onShowCreateFormChange(false)}
              className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-600 flex-shrink-0"
              title="Cancel"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Document items */}
      {documents && documents.length === 0 ? (
        <div className="px-3 py-1.5 text-xs text-slate-400 italic">
          No documents yet
        </div>
      ) : (
        <div className="pb-1">
          {documents?.map((document) => {
            const isSelected = selectedDocumentId === document.id;
            return (
              <div
                key={document.id}
                onClick={() => onSelectDocument(document)}
                className={`group relative flex items-center gap-2 px-2.5 py-2 mx-1 rounded-md cursor-pointer transition-all duration-150 ${
                  isSelected
                    ? "bg-white shadow-sm text-slate-900"
                    : "text-slate-500 hover:bg-slate-200/50 hover:text-slate-700"
                }`}
              >
                {isSelected && (
                  <span className="absolute left-2.5 top-1/2 -translate-y-1/2 w-0.5 h-3 bg-blue-500 rounded-full" />
                )}

                <FileText
                  className={`w-3 h-3 flex-shrink-0 ml-2 ${
                    isSelected ? "text-blue-600" : "text-slate-400"
                  }`}
                />

                <div className="flex-1 min-w-0">
                  <div className={`text-xs truncate leading-none ${isSelected ? "font-semibold text-slate-900" : "text-slate-500"}`}>
                    {document.name}
                  </div>
                </div>

                <button
                  onClick={(e) => onDeleteDocument(e, projectId, document.id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 flex-shrink-0"
                  title="Delete document"
                >
                  <Trash2 className="w-2.5 h-2.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
