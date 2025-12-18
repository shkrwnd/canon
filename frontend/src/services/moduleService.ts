import apiClient from "../clients/apiClient";
import { API_ENDPOINTS } from "../utils/constants";
import { Module, ModuleCreate, ModuleUpdate } from "../types";

export const getModules = async (): Promise<Module[]> => {
  const response = await apiClient.get<Module[]>(API_ENDPOINTS.MODULES.LIST);
  return response.data;
};

export const getModule = async (id: number): Promise<Module> => {
  const response = await apiClient.get<Module>(API_ENDPOINTS.MODULES.GET(id));
  return response.data;
};

export const createModule = async (data: ModuleCreate): Promise<Module> => {
  const response = await apiClient.post<Module>(API_ENDPOINTS.MODULES.CREATE, data);
  return response.data;
};

export const updateModule = async (id: number, data: ModuleUpdate): Promise<Module> => {
  const response = await apiClient.put<Module>(API_ENDPOINTS.MODULES.UPDATE(id), data);
  return response.data;
};

export const deleteModule = async (id: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.MODULES.DELETE(id));
};



