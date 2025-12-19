import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, Plus, Sparkles, MessageSquare, Zap } from "lucide-react";
import { Module } from "../../types";
import { MarkdownEditor } from "../editor/MarkdownEditor";
import { Button } from "../ui";
import { useUpdateModule } from "../../hooks/useModules";

interface DocumentViewProps {
  module: Module | null;
  onCreateModule?: () => void;
  hasModules?: boolean;
}

export const DocumentView: React.FC<DocumentViewProps> = ({ module, onCreateModule, hasModules = false }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const updateModule = useUpdateModule();

  React.useEffect(() => {
    if (module) {
      setEditContent(module.content);
    }
  }, [module]);

  const handleSave = async () => {
    if (!module) return;
    await updateModule.mutateAsync({
      id: module.id,
      data: { content: editContent },
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    if (module) {
      setEditContent(module.content);
    }
    setIsEditing(false);
  };

  if (!module) {
    return (
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-2xl mx-auto px-8 py-12 text-center">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
              <Sparkles className="w-10 h-10 text-blue-600" />
            </div>
          </div>
          
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Welcome to Canon
          </h2>
          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            Create your first living document to get started. Your documents evolve with AI assistance.
          </p>

          {onCreateModule && (
            <Button
              onClick={onCreateModule}
              size="lg"
              className="mb-8 shadow-lg hover:shadow-xl transition-shadow inline-flex items-center"
            >
              <Plus className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>Create Your First Module</span>
            </Button>
          )}

          {hasModules && (
            <p className="text-sm text-gray-500 mb-8">
              Or select a module from the sidebar to continue working
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12 text-left">
            <div className="p-4 rounded-lg bg-white border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900">Living Documents</h3>
              </div>
              <p className="text-sm text-gray-600">
                Your documents are living, breathing entities that evolve with AI assistance
              </p>
            </div>

            <div className="p-4 rounded-lg bg-white border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900">AI-Powered</h3>
              </div>
              <p className="text-sm text-gray-600">
                Chat with AI to update, enhance, and transform your documents naturally
              </p>
            </div>

            <div className="p-4 rounded-lg bg-white border border-gray-200 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900">Quick Actions</h3>
              </div>
              <p className="text-sm text-gray-600">
                Use natural language to edit, search, and manage all your documents
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-xl font-semibold">{module.name}</h2>
        {!isEditing ? (
          <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button onClick={handleSave} size="sm" disabled={updateModule.isPending}>
              Save
            </Button>
            <Button onClick={handleCancel} variant="outline" size="sm">
              Cancel
            </Button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {isEditing ? (
          <MarkdownEditor value={editContent} onChange={setEditContent} height="100%" />
        ) : (
          <div className="prose max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {module.content || "*No content yet*"}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
};



