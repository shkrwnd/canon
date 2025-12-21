import { apiClient } from "../api";
import { API_ENDPOINTS } from "../constants";
import { Document, DocumentCreate, DocumentUpdate } from "../types";

export const getDocuments = async (projectId: number): Promise<Document[]> => {
  const response = await apiClient.get<Document[]>(API_ENDPOINTS.DOCUMENTS.LIST(projectId));
  return response.data;
};

export const getDocument = async (projectId: number, documentId: number): Promise<Document> => {
  const response = await apiClient.get<Document>(API_ENDPOINTS.DOCUMENTS.GET(projectId, documentId));
  return response.data;
};

export const createDocument = async (projectId: number, data: DocumentCreate): Promise<Document> => {
  const response = await apiClient.post<Document>(API_ENDPOINTS.DOCUMENTS.CREATE(projectId), data);
  return response.data;
};

export const updateDocument = async (projectId: number, documentId: number, data: DocumentUpdate): Promise<Document> => {
  const response = await apiClient.put<Document>(API_ENDPOINTS.DOCUMENTS.UPDATE(projectId, documentId), data);
  return response.data;
};

export const deleteDocument = async (projectId: number, documentId: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.DOCUMENTS.DELETE(projectId, documentId));
};


