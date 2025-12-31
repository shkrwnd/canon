import React, { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatMessages } from "../../hooks/useChat";
import { agentAction } from "../../services/agentService";
import { MessageRole, Project, Document } from "../../types";
import { Button, Textarea, useToast } from "../ui";
import { formatRelativeTime } from "../../utils/formatters";
import { FileText } from "lucide-react";

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
    <div className="flex flex-col h-full border-l border-gray-200 bg-white">
      <div className="px-4 py-3 border-b border-gray-200 bg-white">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">Chat</h3>
        <p className="text-xs text-gray-500">{project.name}</p>
        {document && (
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
            <FileText className="w-3 h-3" />
            <span>{document.name}</span>
          </p>
        )}
      </div>
      <div className="flex-1 overflow-auto px-4 py-4 space-y-3 bg-gray-50/30">
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
                  className={`${message.role === MessageRole.USER ? "max-w-[80%]" : "w-full"} rounded-lg px-3 py-2.5 ${
                    message.role === MessageRole.USER
                      ? "bg-blue-600 text-white"
                      : "bg-white border border-gray-200 text-gray-900"
                  }`}
                >
                  <div className={`text-sm prose prose-sm max-w-none ${
                    message.role === MessageRole.USER 
                      ? "prose-invert [&_*]:text-white [&_strong]:font-semibold [&_strong]:text-white [&_em]:text-white [&_code]:bg-blue-700 [&_code]:text-white [&_code]:px-1 [&_code]:rounded [&_pre]:bg-blue-700 [&_pre]:text-white [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-100 [&_a]:underline [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4"
                      : "[&_code]:bg-gray-100 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-100 [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-600 [&_a]:underline"
                  }`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                  <div
                    className={`text-xs mt-1.5 opacity-70 ${
                      message.role === MessageRole.USER ? "text-blue-50" : "text-gray-400"
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
                  className={`${message.role === MessageRole.USER ? "max-w-[80%]" : "w-full"} rounded-lg px-3 py-2.5 ${
                    message.role === MessageRole.USER
                      ? "bg-blue-600 text-white"
                      : "bg-white border border-gray-200 text-gray-900"
                  }`}
                >
                  <div className={`text-sm prose prose-sm max-w-none ${
                    message.role === MessageRole.USER 
                      ? "prose-invert [&_*]:text-white [&_strong]:font-semibold [&_strong]:text-white [&_em]:text-white [&_code]:bg-blue-700 [&_code]:text-white [&_code]:px-1 [&_code]:rounded [&_pre]:bg-blue-700 [&_pre]:text-white [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-100 [&_a]:underline [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-4"
                      : "[&_code]:bg-gray-100 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-100 [&_pre]:p-2 [&_pre]:rounded [&_a]:text-blue-600 [&_a]:underline"
                  }`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                  <div
                    className={`text-xs mt-1.5 opacity-70 ${
                      message.role === MessageRole.USER ? "text-blue-50" : "text-gray-400"
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
                <div className="rounded-lg px-3 py-2 bg-white border border-gray-200">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1.4s' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s', animationDuration: '1.4s' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s', animationDuration: '1.4s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {(!messages || messages.length === 0) && optimisticMessages.length === 0 && (
              <div className="text-center text-gray-400 text-sm py-8">
                No messages yet. Start a conversation.
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="px-4 py-3 border-t border-gray-200 bg-white">
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
            placeholder="Type a message..."
            rows={2}
            disabled={isSending}
            className="resize-none text-sm"
          />
          <Button 
            onClick={handleSend} 
            disabled={isSending || !inputValue.trim()}
            className="self-end"
            size="sm"
          >
            {isSending ? "..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
};



