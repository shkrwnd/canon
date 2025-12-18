import React from "react";
import { ResizablePanel } from "./ResizablePanel";
import { ChatPanel } from "./ChatPanel";
import { Module } from "../types";

interface RightSidebarProps {
  module: Module | null;
  chatId: number | null;
  onChatCreated: (chatId: number) => void;
  onModuleUpdated: (module: Module) => void;
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  module,
  chatId,
  onChatCreated,
  onModuleUpdated,
}) => {
  return (
    <ResizablePanel side="right" initialWidth={320} minWidth={200} maxWidth={600}>
      <ChatPanel
        module={module}
        chatId={chatId}
        onChatCreated={onChatCreated}
        onModuleUpdated={onModuleUpdated}
      />
    </ResizablePanel>
  );
};

