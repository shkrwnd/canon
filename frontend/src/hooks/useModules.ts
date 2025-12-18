import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModules, getModule, createModule, updateModule, deleteModule } from "../services/moduleService";
import { Module, ModuleCreate, ModuleUpdate } from "../types";

export const useModules = () => {
  return useQuery<Module[]>({
    queryKey: ["modules"],
    queryFn: getModules,
  });
};

export const useModule = (id: number | null) => {
  return useQuery<Module>({
    queryKey: ["module", id],
    queryFn: () => getModule(id!),
    enabled: id !== null,
  });
};

export const useCreateModule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ModuleCreate) => createModule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modules"] });
    },
  });
};

export const useUpdateModule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ModuleUpdate }) => updateModule(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["modules"] });
      queryClient.invalidateQueries({ queryKey: ["module", variables.id] });
    },
  });
};

export const useDeleteModule = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteModule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modules"] });
    },
  });
};



