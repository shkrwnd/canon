import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { FileText, Plus, Sparkles, MessageSquare, Zap } from "lucide-react";
import { Document } from "../../types";
import { MarkdownEditor } from "../editor/MarkdownEditor";
import { Button } from "../ui";
import { useUpdateDocument } from "../../hooks/useDocuments";
import { fixMarkdownTables } from "../../utils/markdownUtils";

interface DocumentViewProps {
  document: Document | null;
  projectId: number | null;
  onCreateDocument?: () => void;
  hasDocuments?: boolean;
}

/**
 * Cleans markdown content by fixing table formatting
 * The LLM should output pure markdown, but we ensure tables are properly formatted
 */
const cleanMarkdownContent = (content: string): string => {
  if (!content) return content;
  return fixMarkdownTables(content);
};

export const DocumentView: React.FC<DocumentViewProps> = ({ document, projectId, onCreateDocument, hasDocuments = false }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const updateDocument = useUpdateDocument();

  React.useEffect(() => {
    if (document) {
      setEditContent(document.content);
    }
  }, [document]);

  const handleSave = async () => {
    if (!document || !projectId) return;
    await updateDocument.mutateAsync({
      projectId,
      documentId: document.id,
      data: { content: editContent },
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    if (document) {
      setEditContent(document.content);
    }
    setIsEditing(false);
  };

  if (!document) {
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

          {onCreateDocument && (
            <Button
              onClick={onCreateDocument}
              size="lg"
              className="mb-8 shadow-lg hover:shadow-xl transition-shadow inline-flex items-center"
            >
              <Plus className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>Create Your First Document</span>
            </Button>
          )}

          {hasDocuments && (
            <p className="text-sm text-gray-500 mb-8">
              Or select a document from the sidebar to continue working
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
        <h2 className="text-xl font-semibold">{document.name}</h2>
        {!isEditing ? (
          <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button onClick={handleSave} size="sm" disabled={updateDocument.isPending}>
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
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" />
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-4 -mx-4 px-4">
                    <table className="min-w-full border-collapse border border-gray-300">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-gray-50">
                    {children}
                  </thead>
                ),
                tbody: ({ children }) => <tbody>{children}</tbody>,
                tr: ({ children }) => (
                  <tr className="border-b border-gray-300">
                    {children}
                  </tr>
                ),
                th: ({ children }) => (
                  <th className="px-4 py-2 text-left font-semibold border-r border-gray-300 last:border-r-0">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-2 border-r border-gray-300 last:border-r-0">
                    {children}
                  </td>
                ),
              } as Components}
            >
              {cleanMarkdownContent(document.content || "*No content yet*")}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
};



