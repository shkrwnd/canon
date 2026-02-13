declare global {
  interface Window {
    APP_CONFIG?: { API_URL?: string };
  }
}

export const API_BASE_URL =
  (typeof window !== "undefined" && window.APP_CONFIG?.API_URL) ||
  process.env.REACT_APP_API_URL ||
  "http://localhost:8000";

export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: "/api/auth/register",
    LOGIN: "/api/auth/login",
  },
  PROJECTS: {
    LIST: "/api/projects",
    CREATE: "/api/projects",
    GET: (id: number) => `/api/projects/${id}`,
    UPDATE: (id: number) => `/api/projects/${id}`,
    DELETE: (id: number) => `/api/projects/${id}`,
  },
  DOCUMENTS: {
    LIST: (projectId: number) => `/api/projects/${projectId}/documents`,
    CREATE: (projectId: number) => `/api/projects/${projectId}/documents`,
    GET: (projectId: number, documentId: number) => `/api/projects/${projectId}/documents/${documentId}`,
    UPDATE: (projectId: number, documentId: number) => `/api/projects/${projectId}/documents/${documentId}`,
    DELETE: (projectId: number, documentId: number) => `/api/projects/${projectId}/documents/${documentId}`,
  },
  CHATS: {
    LIST: "/api/chats",
    CREATE: "/api/chats",
    GET_BY_PROJECT: (projectId: number) => `/api/chats/project/${projectId}`,
    GET_MESSAGES: (id: number) => `/api/chats/${id}/messages`,
    ADD_MESSAGE: (id: number) => `/api/chats/${id}/messages`,
  },
  AGENT: {
    ACT: "/api/agent/act",
  },
};

