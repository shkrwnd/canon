import React, { useState, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatMessages } from "../../hooks/useChat";
import { agentAction } from "../../services/agentService";
import { MessageRole, Project, Document } from "../../types";
import { useToast } from "../ui";
import { formatRelativeTime } from "../../utils/formatters";
import { FileText, Send } from "lucide-react";
import { cn } from "../../utils/cn";

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
  const [optimisticMessages, setOptimisticMessages] = useState<
    Array<{
      id: string;
      content: string;
      role: MessageRole;
      created_at: string;
    }>
  >([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setLocalChatId(chatId);
    setOptimisticMessages([]);
  }, [chatId]);

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

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const optimisticUserMessage = {
      id: `optimistic-${Date.now()}`,
      content: userMessage,
      role: MessageRole.USER,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages([optimisticUserMessage]);

    try {
      const response = await agentAction({
        message: userMessage,
        project_id: project.id,
        document_id: document?.id || undefined,
        chat_id: localChatId || undefined,
      });

      const newChatId = response.chat_message.chat_id;
      const finalChatId = newChatId || localChatId;

      if (newChatId && !localChatId) {
        setLocalChatId(newChatId);
        if (onChatCreated) {
          onChatCreated(newChatId);
        }
      }

      if (response.document && onDocumentUpdated) {
        onDocumentUpdated(response.document);
      }

      setOptimisticMessages([]);

      if (finalChatId) {
        queryClient.invalidateQueries({
          queryKey: ["chatMessages", finalChatId],
        });
      }

      if (project.id) {
        queryClient.invalidateQueries({
          queryKey: ["documents", project.id],
        });
      }
      if (document?.id) {
        queryClient.invalidateQueries({
          queryKey: ["document", project.id, document.id],
        });
      }
    } catch (error: any) {
      setOptimisticMessages([]);
      showToast(
        error.response?.data?.detail || "Failed to send message",
        "error"
      );
      setInputValue(userMessage);
    } finally {
      setIsSending(false);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Auto-resize
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-slate-50 border-l border-slate-200">
        <div className="w-12 h-12 rounded-2xl bg-slate-200 flex items-center justify-center mb-4">
          <svg width="18" height="18" viewBox="0 0 12 12" fill="none">
            <path
              d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
              fill="#475569"
            />
          </svg>
        </div>
        <p className="text-sm font-semibold text-slate-700">No project selected</p>
        <p className="text-xs text-slate-400 mt-1.5 text-center max-w-[160px] leading-relaxed">
          Select a project from the sidebar to start chatting
        </p>
      </div>
    );
  }

  const allMessages = [
    ...(messages || []),
    ...optimisticMessages,
  ];

  const isEmpty =
    (!messages || messages.length === 0) && optimisticMessages.length === 0;

  return (
    <div className="flex flex-col h-full bg-slate-50 border-l border-slate-200">
      {/* Chat header */}
      <div className="px-4 py-3 bg-white border-b border-slate-100 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-800 truncate tracking-tight">
              {project.name}
            </p>
            {document && (
              <div className="flex items-center gap-1 mt-0.5">
                <FileText className="w-3 h-3 text-slate-400 flex-shrink-0" />
                <span className="text-xs text-slate-400 truncate">
                  {document.name}
                </span>
              </div>
            )}
          </div>
          <div className="w-6 h-6 rounded-lg bg-blue-700 flex items-center justify-center flex-shrink-0 ml-2">
            <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
              <path
                d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
                fill="white"
                fillOpacity="0.9"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-4 py-5 space-y-5">
        {isLoading && !optimisticMessages.length ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex gap-1.5">
              {[0, 0.15, 0.3].map((delay, i) => (
                <div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce"
                  style={{ animationDelay: `${delay}s`, animationDuration: "1.2s" }}
                />
              ))}
            </div>
          </div>
        ) : isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-slate-200 flex items-center justify-center mb-4">
              <svg width="18" height="18" viewBox="0 0 12 12" fill="none">
                <path
                  d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
                  fill="#475569"
                />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-700 mb-1.5">
              Start a conversation
            </p>
            <p className="text-xs text-slate-400 max-w-[180px] leading-relaxed">
              Ask AI to help create or update your documents
            </p>
          </div>
        ) : (
          <>
            {allMessages.map((message) => {
              const isUser = message.role === MessageRole.USER;
              return (
                <div
                  key={message.id}
                  className={cn("flex items-end gap-2.5", isUser ? "justify-end" : "justify-start")}
                >
                  {!isUser && (
                    <div className="w-6 h-6 rounded-lg bg-blue-700 flex items-center justify-center flex-shrink-0 mb-5">
                      <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                        <path
                          d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
                          fill="white"
                          fillOpacity="0.9"
                        />
                      </svg>
                    </div>
                  )}
                  <div className={cn(isUser ? "max-w-[85%]" : "flex-1 min-w-0")}>
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                        isUser
                          ? "bg-blue-600 text-white rounded-br-md"
                          : "bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm"
                      )}
                      style={!isUser ? { borderColor: '#E7E5E4' } : {}}
                    >
                      <div
                        className={cn(
                          "prose prose-sm max-w-none",
                          isUser
                            ? "prose-invert [&_*]:text-white [&_strong]:font-semibold [&_code]:bg-blue-500 [&_code]:px-1.5 [&_code]:rounded [&_pre]:bg-blue-800 [&_pre]:p-3 [&_pre]:rounded-lg [&_a]:text-blue-200 [&_a]:underline"
                            : "[&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:rounded [&_code]:text-slate-700 [&_pre]:bg-slate-100 [&_pre]:p-3 [&_pre]:rounded-lg [&_a]:text-blue-700 [&_a]:underline [&_p]:text-slate-700 [&_li]:text-slate-700"
                        )}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                    <p
                      className={cn(
                        "text-[11px] mt-1.5 text-slate-400",
                        isUser ? "text-right" : "text-left"
                      )}
                    >
                      {String(message.id).startsWith("optimistic")
                        ? "just now"
                        : formatRelativeTime(message.created_at)}
                    </p>
                  </div>
                </div>
              );
            })}

            {/* Typing indicator */}
            {isSending && optimisticMessages.length > 0 && (
              <div className="flex items-end gap-2.5 justify-start">
                <div className="w-6 h-6 rounded-lg bg-blue-700 flex items-center justify-center flex-shrink-0 mb-5">
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2 2h3.5v3.5H2V2zM6.5 2H10v3.5H6.5V2zM2 6.5h3.5V10H2V6.5zM6.5 6.5H10V10H6.5V6.5z"
                      fill="white"
                      fillOpacity="0.9"
                    />
                  </svg>
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                  <div className="flex gap-1 items-center h-4">
                    {[0, 0.2, 0.4].map((delay, i) => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-blue-300 animate-bounce"
                        style={{ animationDelay: `${delay}s`, animationDuration: "1.4s" }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="px-4 py-4 bg-white border-t border-slate-100 flex-shrink-0">
        <div className="flex items-end gap-2.5 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 focus-within:bg-white transition-all">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleTextareaInput}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              document
                ? `Ask about "${document.name}"...`
                : "Ask AI anything..."
            }
            rows={1}
            disabled={isSending}
            className="flex-1 bg-transparent border-0 outline-none resize-none text-sm text-slate-800 placeholder-slate-400 min-h-[20px] max-h-[120px] py-0.5 disabled:opacity-50"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={handleSend}
            disabled={isSending || !inputValue.trim()}
            className={cn(
              "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-150",
              inputValue.trim() && !isSending
                ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            )}
          >
            {isSending ? (
              <div className="w-3 h-3 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
        <p className="text-[11px] text-slate-400 mt-2 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};
