import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { FileText, Plus, Sparkles, MessageSquare, Zap, ArrowRight, Lightbulb } from "lucide-react";
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
    const examplePrompts = [
      "Create a project plan",
      "Write a blog post",
      "Make a meeting notes template"
    ];

    const features = [
      {
        icon: FileText,
        title: "Living Documents",
        description: "Your documents are living, breathing entities that evolve with AI assistance",
        example: "Ask AI to update your content",
        color: "blue",
        iconBg: "bg-blue-100",
        iconColor: "text-blue-600",
        borderColor: "hover:border-blue-300"
      },
      {
        icon: MessageSquare,
        title: "AI-Powered",
        description: "Chat with AI to update, enhance, and transform your documents naturally",
        example: "Try: 'Add a conclusion section'",
        color: "purple",
        iconBg: "bg-purple-100",
        iconColor: "text-purple-600",
        borderColor: "hover:border-purple-300"
      },
      {
        icon: Zap,
        title: "Quick Actions",
        description: "Use natural language to edit, search, and manage all your documents",
        example: "Say: 'Update the introduction'",
        color: "green",
        iconBg: "bg-green-100",
        iconColor: "text-green-600",
        borderColor: "hover:border-green-300"
      }
    ];

    if (hasDocuments) {
      // Better empty state for existing users
      return (
        <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-white overflow-auto">
          <div className="max-w-2xl mx-auto px-8 py-8 text-center">
            <div className="flex justify-center mb-6">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-100 via-blue-200 to-blue-300 flex items-center justify-center shadow-lg">
                <FileText className="w-12 h-12 text-blue-700" />
              </div>
            </div>
            
            <h2 className="text-3xl font-bold text-gray-900 mb-3">
              Select a Document
            </h2>
            <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
              Choose a document from the sidebar to continue working, or create a new one to get started.
            </p>

            {onCreateDocument && (
              <div className="flex gap-3 justify-center">
                <Button
                  onClick={onCreateDocument}
                  size="lg"
                  className="shadow-lg hover:shadow-xl inline-flex items-center bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold px-8 py-4 text-lg"
                >
                  <Plus className="w-5 h-5 mr-2 flex-shrink-0" />
                  <span>New Document</span>
                  <ArrowRight className="w-5 h-5 ml-2 flex-shrink-0" />
                </Button>
              </div>
            )}

            {/* Helpful Tips Section */}
            <div className="mt-12 p-6 bg-blue-50 rounded-xl border-l-4 border-blue-500 max-w-lg mx-auto">
              <div className="flex items-start gap-3">
                <Lightbulb className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900 mb-1">💡 Pro Tip</p>
                  <p className="text-sm text-gray-700">
                    You can reference documents by name in the chat. Try saying "update the Blog Post document" to edit specific documents.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    // Full welcome page for new users
    return (
      <div className="h-full bg-gradient-to-br from-gray-50 via-white to-gray-50 flex items-center justify-center">
        <div className="max-w-4xl mx-auto px-8 py-6 w-full">
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-100 via-blue-200 to-blue-300 flex items-center justify-center shadow-lg animate-fade-in">
                <Sparkles className="w-10 h-10 text-blue-700" />
              </div>
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Welcome to Canon
            </h2>
            <p className="text-base text-gray-600 mb-4 max-w-xl mx-auto">
              Create your first living document to get started. Your documents evolve with AI assistance.
            </p>

            {onCreateDocument && (
              <Button
                onClick={onCreateDocument}
                size="lg"
                className="mb-4 shadow-lg hover:shadow-xl inline-flex items-center bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold px-6 py-2.5 text-sm"
              >
                <Plus className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>Create Your First Document</span>
                <ArrowRight className="w-4 h-4 ml-2 flex-shrink-0" />
              </Button>
            )}

            {/* Example Prompts */}
            {onCreateDocument && (
              <div className="mb-5">
                <p className="text-xs font-medium text-gray-700 mb-2">Try these examples:</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {examplePrompts.map((example, idx) => (
                    <button
                      key={idx}
                      onClick={onCreateDocument}
                      className="px-3 py-1.5 text-xs bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-blue-400 hover:text-blue-600 font-medium"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Feature Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            {features.map((feature, idx) => {
              const IconComponent = feature.icon;
              return (
                <div
                  key={idx}
                  className={`p-4 rounded-lg bg-white border border-gray-200 shadow-sm hover:shadow-md ${feature.borderColor} cursor-pointer group`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className={`w-8 h-8 rounded-lg ${feature.iconBg} flex items-center justify-center`}>
                      <IconComponent className={`w-4 h-4 ${feature.iconColor}`} />
                    </div>
                    <h3 className="font-semibold text-gray-900 text-sm">{feature.title}</h3>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">
                    {feature.description}
                  </p>
                  <p className="text-xs text-gray-500 italic">
                    {feature.example}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Getting Started Guide - Compact */}
          <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2 text-sm">
              <Zap className="w-4 h-4 text-blue-600" />
              Quick Start
            </h3>
            <ol className="space-y-2 text-xs text-gray-700">
              <li className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold">1</span>
                <span className="text-gray-700">Create your first document or project</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold">2</span>
                <span className="text-gray-700">Start chatting with AI to edit your content</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold">3</span>
                <span className="text-gray-700">Watch your documents evolve in real-time</span>
              </li>
            </ol>
          </div>

          {/* Helpful Tips Section - Compact */}
          <div className="p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
            <div className="flex items-start gap-2">
              <Lightbulb className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-gray-900 mb-1">💡 Pro Tip</p>
                <p className="text-xs text-gray-700">
                  Reference documents by name in chat. Try "update the Blog Post document" to edit specific documents.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-white to-gray-50/50 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{document.name}</h2>
          <p className="text-xs text-gray-500 mt-1">Living Document</p>
        </div>
        {!isEditing ? (
          <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button onClick={handleSave} size="sm" disabled={updateDocument.isPending}>
              {updateDocument.isPending ? "Saving..." : "Save"}
            </Button>
            <Button onClick={handleCancel} variant="outline" size="sm">
              Cancel
            </Button>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto bg-gradient-to-b from-white to-gray-50/30">
        <div className="max-w-4xl mx-auto px-8 py-8">
        {isEditing ? (
          <MarkdownEditor value={editContent} onChange={setEditContent} height="100%" />
        ) : (
          <div className="prose prose-lg max-w-none prose-headings:font-bold prose-headings:text-gray-900 prose-p:text-gray-700 prose-p:leading-relaxed prose-a:text-blue-600 prose-a:no-underline prose-a:border-b prose-a:border-blue-300 prose-a:hover:border-blue-600 prose-strong:text-gray-900 prose-strong:font-semibold prose-code:text-red-600 prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-medium prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-gray-700">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="transition-colors" />
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-6 -mx-4 px-4">
                    <table className="min-w-full border-collapse border-2 border-gray-200 rounded-lg shadow-sm">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                    {children}
                  </thead>
                ),
                tbody: ({ children }) => <tbody className="bg-white">{children}</tbody>,
                tr: ({ children }) => (
                  <tr className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                    {children}
                  </tr>
                ),
                th: ({ children }) => (
                  <th className="px-4 py-3 text-left font-semibold text-gray-900 border-r border-gray-200 last:border-r-0">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-3 border-r border-gray-200 last:border-r-0 text-gray-700">
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
    </div>
  );
};



