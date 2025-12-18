import { apiClient } from "../api";
import { API_ENDPOINTS } from "../constants";
import { Token, UserRegister, UserLogin } from "../types";
import { setAuthToken, removeAuthToken } from "../utils/auth.utils";

export const register = async (data: UserRegister): Promise<Token> => {
  const response = await apiClient.post<Token>(API_ENDPOINTS.AUTH.REGISTER, data);
  setAuthToken(response.data.access_token);
  return response.data;
};

export const login = async (data: UserLogin): Promise<Token> => {
  const response = await apiClient.post<Token>(API_ENDPOINTS.AUTH.LOGIN, data);
  setAuthToken(response.data.access_token);
  return response.data;
};

export const logout = (): void => {
  removeAuthToken();
};

