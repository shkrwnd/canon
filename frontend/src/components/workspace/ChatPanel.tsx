import React, { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatMessages } from "../../hooks/useChat";
import { agentAction } from "../../services/agentService";
import { MessageRole, Module } from "../../types";
import { Button, Textarea } from "../ui";
import { formatRelativeTime } from "../../utils/formatters";

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
  const queryClient = useQueryClient();
  const [localChatId, setLocalChatId] = useState<number | null>(chatId);
  const { data: messages, isLoading } = useChatMessages(localChatId);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<Array<{id: string, content: string, role: MessageRole, created_at: string}>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update local chatId when prop changes
  useEffect(() => {
    if (chatId !== null) {
      setLocalChatId(chatId);
    }
  }, [chatId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, optimisticMessages]);

  const handleSend = async () => {
    if (!inputValue.trim() || !module || isSending) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setIsSending(true);

    // Add optimistic user message immediately
    const optimisticUserMessage = {
      id: `optimistic-${Date.now()}`,
      content: userMessage,
      role: MessageRole.USER,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages([optimisticUserMessage]);

    try {
      // Send agent action
      const response = await agentAction({
        message: userMessage,
        module_id: module.id,
        chat_id: localChatId || undefined,
      });

      // Update chatId if a new chat was created
      const newChatId = response.chat_message.chat_id;
      const finalChatId = newChatId || localChatId;
      
      if (newChatId && !localChatId) {
        setLocalChatId(newChatId);
        if (onChatCreated) {
          onChatCreated(newChatId);
        }
      }

      // If module was updated, notify parent
      if (response.module && onModuleUpdated) {
        onModuleUpdated(response.module);
      }

      // Clear optimistic messages - real messages will come from the API
      setOptimisticMessages([]);

      // Invalidate and refetch messages for this chat
      if (finalChatId) {
        queryClient.invalidateQueries({ queryKey: ["chatMessages", finalChatId] });
      }
      
      // Also invalidate modules to refresh the module list
      queryClient.invalidateQueries({ queryKey: ["modules"] });
      if (module.id) {
        queryClient.invalidateQueries({ queryKey: ["module", module.id] });
      }
    } catch (error: any) {
      // Remove optimistic message on error
      setOptimisticMessages([]);
      alert(error.response?.data?.detail || "Failed to send message");
      // Restore input on error
      setInputValue(userMessage);
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
        <p className="text-xs text-gray-400 mt-1">
          Tip: You can reference other modules by name (e.g., "update the Blog Post module")
        </p>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {isLoading && !optimisticMessages.length ? (
          <div className="text-center text-gray-500">Loading messages...</div>
        ) : (
          <>
            {/* Show actual messages from API */}
            {messages && messages.map((message) => (
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
            ))}
            {/* Show optimistic messages (user's message before API response) */}
            {optimisticMessages.map((message) => (
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
                    just now
                  </div>
                </div>
              </div>
            ))}
            {/* Show loading indicator when waiting for bot response */}
            {isSending && optimisticMessages.length > 0 && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-lg p-3 bg-gray-100 text-gray-900">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1.4s' }}></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s', animationDuration: '1.4s' }}></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s', animationDuration: '1.4s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {(!messages || messages.length === 0) && optimisticMessages.length === 0 && (
              <div className="text-center text-gray-500 text-sm">
                No messages yet. Start a conversation!
              </div>
            )}
          </>
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



