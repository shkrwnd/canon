import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Module } from "../../types";
import { MarkdownEditor } from "../editor/MarkdownEditor";
import { Button } from "../ui";
import { useUpdateModule } from "../../hooks/useModules";

interface DocumentViewProps {
  module: Module | null;
}

export const DocumentView: React.FC<DocumentViewProps> = ({ module }) => {
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
      <div className="flex items-center justify-center h-full text-gray-500">
        Select a module to view its content
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
            <ReactMarkdown>{module.content || "*No content yet*"}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
};



