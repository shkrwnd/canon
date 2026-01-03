import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDocuments, getDocument, createDocument, updateDocument, deleteDocument } from "../services/documentService";
import { Document, DocumentCreate, DocumentUpdate } from "../types";

export const useDocuments = (projectId: number | null) => {
  return useQuery<Document[]>({
    queryKey: ["documents", projectId],
    queryFn: () => getDocuments(projectId!),
    enabled: projectId !== null,
  });
};

export const useDocument = (projectId: number | null, documentId: number | null) => {
  return useQuery<Document>({
    queryKey: ["document", projectId, documentId],
    queryFn: () => getDocument(projectId!, documentId!),
    enabled: projectId !== null && documentId !== null,
  });
};

export const useCreateDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: number; data: DocumentCreate }) => createDocument(projectId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["documents", variables.projectId] });
    },
  });
};

export const useUpdateDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, documentId, data }: { projectId: number; documentId: number; data: DocumentUpdate }) => 
      updateDocument(projectId, documentId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["documents", variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ["document", variables.projectId, variables.documentId] });
    },
  });
};

export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, documentId }: { projectId: number; documentId: number }) => 
      deleteDocument(projectId, documentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["documents", variables.projectId] });
    },
  });
};





