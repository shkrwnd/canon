import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import {
  FileText,
  Plus,
  Pencil,
  Check,
  X,
  ArrowRight,
  Layers,
  MessageSquare,
  Zap,
} from "lucide-react";
import { Document } from "../../types";
import { MarkdownEditor } from "../editor/MarkdownEditor";
import { useUpdateDocument } from "../../hooks/useDocuments";
import { fixMarkdownTables } from "../../utils/markdownUtils";

interface DocumentViewProps {
  document: Document | null;
  projectId: number | null;
  onCreateDocument?: () => void;
  hasDocuments?: boolean;
}

const cleanMarkdownContent = (content: string): string => {
  if (!content) return content;
  return fixMarkdownTables(content);
};

export const DocumentView: React.FC<DocumentViewProps> = ({
  document,
  projectId,
  onCreateDocument,
  hasDocuments = false,
}) => {
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
    if (hasDocuments) {
      return (
        <div className="flex items-center justify-center h-full bg-white overflow-auto">
          <div className="max-w-md mx-auto px-8 py-12 text-center">
            <div className="w-14 h-14 mx-auto mb-6 rounded-2xl bg-slate-100 flex items-center justify-center">
              <FileText className="w-6 h-6 text-slate-400" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2 tracking-tight">
              Select a document
            </h2>
            <p className="text-sm text-slate-500 mb-7 leading-relaxed">
              Choose a document from the sidebar, or create a new one to start writing.
            </p>
            {onCreateDocument && (
              <button
                onClick={onCreateDocument}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Document
              </button>
            )}
          </div>
        </div>
      );
    }

    // Welcome state for new users
    return (
      <div className="h-full bg-white flex items-center justify-center overflow-auto">
        <div className="max-w-lg mx-auto px-10 py-10 w-full">
          {/* Header */}
          <div className="mb-10">
            <div className="w-12 h-12 rounded-2xl bg-blue-700 flex items-center justify-center mb-6">
              <svg width="20" height="20" viewBox="0 0 12 12" fill="none">
                <path
                  d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
                  fill="white"
                  fillOpacity="0.9"
                />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-slate-900 mb-3 tracking-tight">
              Welcome to Canon
            </h2>
            <p className="text-base text-slate-500 leading-relaxed max-w-sm">
              Your documents evolve with AI assistance. Create a project, add documents, and start chatting.
            </p>
          </div>

          {onCreateDocument && (
            <button
              onClick={onCreateDocument}
              className="inline-flex items-center gap-2.5 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors mb-10 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create your first document
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {/* Feature grid */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { icon: Layers, title: "Living Documents", desc: "Documents that evolve via AI" },
              { icon: MessageSquare, title: "AI-Powered", desc: "Natural language editing" },
              { icon: Zap, title: "Quick Actions", desc: "Reference docs by name in chat" },
            ].map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="p-4 rounded-xl bg-blue-50 border border-blue-100 hover:bg-blue-100 transition-colors"
              >
                <div className="w-7 h-7 rounded-lg bg-white border border-blue-200 flex items-center justify-center mb-3 shadow-sm">
                  <Icon className="w-3.5 h-3.5 text-blue-600" />
                </div>
                <p className="text-xs font-bold text-slate-800 mb-1">{title}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>

          {/* Quick start */}
          <div className="p-5 rounded-xl bg-slate-50 border border-slate-100">
            <p className="text-[10px] font-bold text-slate-400 mb-4 uppercase tracking-[0.12em]">
              Quick Start
            </p>
            <ol className="space-y-3">
              {[
                "Create a project in the sidebar",
                "Add a document to your project",
                "Chat with AI to build your content",
              ].map((step, i) => (
                <li key={i} className="flex items-center gap-3 text-sm text-slate-600">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    );
  }

  // Document view
  return (
    <div className="flex flex-col h-full bg-white">
      {/* Document header */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-slate-100">
        <div className="flex-1 min-w-0 mr-4">
          <h1 className="text-xl font-bold text-slate-900 tracking-tight leading-tight">
            {document.name}
          </h1>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
              <span className="w-1 h-1 rounded-full bg-blue-500 inline-block" />
              Living Document
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-colors"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                disabled={updateDocument.isPending}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-sm"
              >
                <Check className="w-3 h-3" />
                {updateDocument.isPending ? "Saving..." : "Save"}
              </button>
              <button
                onClick={handleCancel}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <X className="w-3 h-3" />
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto">
        {isEditing ? (
          <MarkdownEditor value={editContent} onChange={setEditContent} height="100%" />
        ) : (
          <div className="max-w-3xl mx-auto px-8 py-10">
            <div className="prose prose-slate prose-sm max-w-none
              prose-headings:font-bold prose-headings:tracking-tight prose-headings:text-slate-900
              prose-h1:text-2xl prose-h1:mt-0 prose-h1:mb-5
              prose-h2:text-xl prose-h2:mt-10 prose-h2:mb-4
              prose-h3:text-base prose-h3:mt-7 prose-h3:mb-3
              prose-p:text-slate-700 prose-p:leading-7 prose-p:text-[15px]
              prose-a:text-blue-700 prose-a:no-underline prose-a:font-medium hover:prose-a:underline
              prose-strong:text-slate-900 prose-strong:font-bold
              prose-code:text-slate-800 prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-code:font-medium prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-xl prose-pre:text-[13px]
              prose-blockquote:border-l-blue-300 prose-blockquote:text-slate-600 prose-blockquote:not-italic prose-blockquote:bg-blue-50 prose-blockquote:rounded-r-lg prose-blockquote:py-1
              prose-ul:text-slate-700 prose-ol:text-slate-700
              prose-li:text-slate-700
              prose-hr:border-slate-100
              prose-img:rounded-xl prose-img:shadow-sm
            ">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => (
                    <a
                      {...props}
                      target="_blank"
                      rel="noopener noreferrer"
                    />
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-5">
                      <table className="min-w-full border-collapse text-sm">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="border-b border-zinc-200">
                      {children}
                    </thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="divide-y divide-zinc-100">{children}</tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-zinc-50 transition-colors">
                      {children}
                    </tr>
                  ),
                  th: ({ children }) => (
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-zinc-600 uppercase tracking-wider">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-4 py-2.5 text-zinc-700 text-sm">
                      {children}
                    </td>
                  ),
                } as Components}
              >
                {cleanMarkdownContent(document.content || "*No content yet. Click Edit to start writing, or use the chat to have AI generate content.*")}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
