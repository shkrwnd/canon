import axios, { AxiosInstance, AxiosError } from "axios";
import { API_BASE_URL } from "../constants";
import { getAuthToken, removeAuthToken } from "../utils/auth.utils";

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - remove token and redirect to login
      removeAuthToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;



