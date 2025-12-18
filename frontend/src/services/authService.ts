import apiClient from "../clients/apiClient";
import { API_ENDPOINTS } from "../utils/constants";
import { Token, UserRegister, UserLogin, User } from "../types";
import { setAuthToken, removeAuthToken } from "../helpers/authHelpers";

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

