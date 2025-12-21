import { apiClient } from "../api";
import { API_ENDPOINTS } from "../constants";
import { Chat, ChatCreate, ChatMessage, ChatMessageCreate } from "../types";

export const getChats = async (): Promise<Chat[]> => {
  const response = await apiClient.get<Chat[]>(API_ENDPOINTS.CHATS.LIST);
  return response.data;
};

export const createChat = async (data: ChatCreate): Promise<Chat> => {
  const response = await apiClient.post<Chat>(API_ENDPOINTS.CHATS.CREATE, data);
  return response.data;
};

export const getChatByProject = async (projectId: number): Promise<Chat> => {
  const response = await apiClient.get<Chat>(API_ENDPOINTS.CHATS.GET_BY_PROJECT(projectId));
  return response.data;
};

export const getChatMessages = async (chatId: number): Promise<ChatMessage[]> => {
  const response = await apiClient.get<ChatMessage[]>(API_ENDPOINTS.CHATS.GET_MESSAGES(chatId));
  return response.data;
};

export const addChatMessage = async (chatId: number, data: ChatMessageCreate): Promise<ChatMessage> => {
  const response = await apiClient.post<ChatMessage>(API_ENDPOINTS.CHATS.ADD_MESSAGE(chatId), data);
  return response.data;
};



