export const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: "/api/auth/register",
    LOGIN: "/api/auth/login",
  },
  MODULES: {
    LIST: "/api/modules",
    CREATE: "/api/modules",
    GET: (id: number) => `/api/modules/${id}`,
    UPDATE: (id: number) => `/api/modules/${id}`,
    DELETE: (id: number) => `/api/modules/${id}`,
  },
  CHATS: {
    LIST: "/api/chats",
    CREATE: "/api/chats",
    GET_MESSAGES: (id: number) => `/api/chats/${id}/messages`,
    ADD_MESSAGE: (id: number) => `/api/chats/${id}/messages`,
  },
  AGENT: {
    ACT: "/api/agent/act",
  },
};

export const STORAGE_KEYS = {
  AUTH_TOKEN: "canon_auth_token",
};



