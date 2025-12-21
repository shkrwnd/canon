import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getChats, getChatMessages, createChat, addChatMessage, getChatByProject } from "../services/chatService";
import { Chat, ChatCreate, ChatMessage, ChatMessageCreate } from "../types";

export const useChats = () => {
  return useQuery<Chat[]>({
    queryKey: ["chats"],
    queryFn: getChats,
  });
};

export const useChatMessages = (chatId: number | null) => {
  return useQuery<ChatMessage[]>({
    queryKey: ["chatMessages", chatId],
    queryFn: () => getChatMessages(chatId!),
    enabled: chatId !== null,
  });
};

export const useCreateChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ChatCreate) => createChat(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
};

export const useAddChatMessage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId, data }: { chatId: number; data: ChatMessageCreate }) =>
      addChatMessage(chatId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chatMessages", variables.chatId] });
    },
  });
};

export const useChatByProject = (projectId: number | null) => {
  return useQuery<Chat>({
    queryKey: ["chat", "project", projectId],
    queryFn: () => getChatByProject(projectId!),
    enabled: projectId !== null,
  });
};



