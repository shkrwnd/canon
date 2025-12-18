import React, { useState, useEffect, useRef } from "react";
import { useChatMessages, useAddChatMessage } from "../hooks/useChat";
import { useModule } from "../hooks/useModules";
import { agentAction } from "../services/agentService";
import { ChatMessage, MessageRole, Module } from "../types";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { formatRelativeTime } from "../utils/formatters";

interface ChatPanelProps {
  module: Module | null;
  chatId: number | null;
  onChatCreated?: (chatId: number) => void;
  onModuleUpdated?: (module: Module) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  module,
  chatId,
  onChatCreated,
  onModuleUpdated,
}) => {
  const { data: messages, isLoading } = useChatMessages(chatId);
  const addMessage = useAddChatMessage();
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || !module || isSending) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setIsSending(true);

    try {
      // Send agent action
      const response = await agentAction({
        message: userMessage,
        module_id: module.id,
        chat_id: chatId || undefined,
      });

      // If chat was created, notify parent
      if (response.chat_message.chat_id && !chatId && onChatCreated) {
        onChatCreated(response.chat_message.chat_id);
      }

      // If module was updated, notify parent
      if (response.module && onModuleUpdated) {
        onModuleUpdated(response.module);
      }

      // Refresh messages
      window.location.reload(); // Simple refresh for now
    } catch (error: any) {
      alert(error.response?.data?.detail || "Failed to send message");
    } finally {
      setIsSending(false);
    }
  };

  if (!module) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Select a module to start chatting
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full border-l">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Chat</h3>
        <p className="text-sm text-gray-500">{module.name}</p>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {isLoading ? (
          <div className="text-center text-gray-500">Loading messages...</div>
        ) : messages && messages.length > 0 ? (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === MessageRole.USER ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.role === MessageRole.USER
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                <div
                  className={`text-xs mt-1 ${
                    message.role === MessageRole.USER ? "text-blue-100" : "text-gray-500"
                  }`}
                >
                  {formatRelativeTime(message.created_at)}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center text-gray-500 text-sm">
            No messages yet. Start a conversation!
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Type your message..."
            rows={2}
            disabled={isSending}
          />
          <Button onClick={handleSend} disabled={isSending || !inputValue.trim()}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};



