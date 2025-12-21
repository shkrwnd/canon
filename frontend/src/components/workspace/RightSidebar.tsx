import React from "react";
import { ResizablePanel } from "./ResizablePanel";
import { ChatPanel } from "./ChatPanel";
import { Project, Document } from "../../types";

interface RightSidebarProps {
  project: Project | null;
  document: Document | null;
  chatId: number | null;
  onChatCreated: (chatId: number) => void;
  onDocumentUpdated: (document: Document) => void;
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  project,
  document,
  chatId,
  onChatCreated,
  onDocumentUpdated,
}) => {
  return (
    <ResizablePanel side="right" initialWidth={320} minWidth={200} maxWidth={600}>
      <ChatPanel
        project={project}
        document={document}
        chatId={chatId}
        onChatCreated={onChatCreated}
        onDocumentUpdated={onDocumentUpdated}
      />
    </ResizablePanel>
  );
};

