import React, { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatMessages } from "../../hooks/useChat";
import { agentAction } from "../../services/agentService";
import { MessageRole, Project, Document } from "../../types";
import { Button, Textarea, useToast } from "../ui";
import { formatRelativeTime } from "../../utils/formatters";

interface ChatPanelProps {
  project: Project | null;
  document: Document | null;
  chatId: number | null;
  onChatCreated?: (chatId: number) => void;
  onDocumentUpdated?: (document: Document) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  project,
  document,
  chatId,
  onChatCreated,
  onDocumentUpdated,
}) => {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [localChatId, setLocalChatId] = useState<number | null>(chatId);
  const { data: messages, isLoading } = useChatMessages(localChatId);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<Array<{id: string, content: string, role: MessageRole, created_at: string}>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update local chatId when prop changes (including when it becomes null)
  useEffect(() => {
    setLocalChatId(chatId);
    // Clear optimistic messages when chat changes
    setOptimisticMessages([]);
  }, [chatId]);

  // Reset chat state when project changes
  useEffect(() => {
    setLocalChatId(null);
    setOptimisticMessages([]);
    setInputValue("");
  }, [project?.id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, optimisticMessages]);

  const handleSend = async () => {
    if (!inputValue.trim() || !project || isSending) return;

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
        project_id: project.id,
        document_id: document?.id || undefined,
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

      // If document was updated, notify parent
      if (response.document && onDocumentUpdated) {
        onDocumentUpdated(response.document);
      }

      // Clear optimistic messages - real messages will come from the API
      setOptimisticMessages([]);

      // Invalidate and refetch messages for this chat
      if (finalChatId) {
        queryClient.invalidateQueries({ queryKey: ["chatMessages", finalChatId] });
      }
      
      // Also invalidate documents to refresh the document list
      if (project.id) {
        queryClient.invalidateQueries({ queryKey: ["documents", project.id] });
      }
      if (document?.id) {
        queryClient.invalidateQueries({ queryKey: ["document", project.id, document.id] });
      }
    } catch (error: any) {
      // Remove optimistic message on error
      setOptimisticMessages([]);
      showToast(error.response?.data?.detail || "Failed to send message", "error");
      // Restore input on error
      setInputValue(userMessage);
    } finally {
      setIsSending(false);
    }
  };

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Select a project to start chatting
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full border-l">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Chat</h3>
        <p className="text-sm text-gray-500">{project.name}</p>
        {document && (
          <p className="text-xs text-gray-400 mt-1">
            Current document: {document.name}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-1">
          Tip: You can reference documents by name (e.g., "update the Blog Post document")
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
                  className={`${message.role === MessageRole.USER ? "max-w-[80%]" : "w-full"} rounded-lg p-3 ${
                    message.role === MessageRole.USER
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  <div className={`text-sm prose prose-sm max-w-none ${
                    message.role === MessageRole.USER 
                      ? "prose-invert [&_*]:text-white [&_strong]:font-bold [&_strong]:text-white [&_em]:text-white [&_code]:bg-blue-500 [&_code]:text-white [&_code]:px-1 [&_code]:rounded [&_pre]:bg-blue-500 [&_pre]:text-white [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-200 [&_a]:underline [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4"
                      : "[&_code]:bg-gray-200 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-200 [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-600 [&_a]:underline"
                  }`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
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
                  className={`${message.role === MessageRole.USER ? "max-w-[80%]" : "w-full"} rounded-lg p-3 ${
                    message.role === MessageRole.USER
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  <div className={`text-sm prose prose-sm max-w-none ${
                    message.role === MessageRole.USER 
                      ? "prose-invert [&_*]:text-white [&_strong]:font-bold [&_strong]:text-white [&_em]:text-white [&_code]:bg-blue-500 [&_code]:text-white [&_code]:px-1 [&_code]:rounded [&_pre]:bg-blue-500 [&_pre]:text-white [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-200 [&_a]:underline [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4"
                      : "[&_code]:bg-gray-200 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-200 [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-600 [&_a]:underline"
                  }`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
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
              <div className="flex justify-center">
                <div className="rounded-lg p-3 bg-gray-100 text-gray-900">
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



