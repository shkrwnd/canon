import { apiClient } from "../api";
import { API_ENDPOINTS } from "../constants";
import { Project, ProjectCreate, ProjectUpdate } from "../types";

export const getProjects = async (): Promise<Project[]> => {
  const response = await apiClient.get<Project[]>(API_ENDPOINTS.PROJECTS.LIST);
  return response.data;
};

export const getProject = async (id: number): Promise<Project> => {
  const response = await apiClient.get<Project>(API_ENDPOINTS.PROJECTS.GET(id));
  return response.data;
};

export const createProject = async (data: ProjectCreate): Promise<Project> => {
  const response = await apiClient.post<Project>(API_ENDPOINTS.PROJECTS.CREATE, data);
  return response.data;
};

export const updateProject = async (id: number, data: ProjectUpdate): Promise<Project> => {
  const response = await apiClient.put<Project>(API_ENDPOINTS.PROJECTS.UPDATE(id), data);
  return response.data;
};

export const deleteProject = async (id: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.PROJECTS.DELETE(id));
};



