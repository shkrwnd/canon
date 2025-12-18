import { apiClient } from "../api";
import { API_ENDPOINTS } from "../constants";
import { AgentActionRequest, AgentActionResponse } from "../types";

export const agentAction = async (data: AgentActionRequest): Promise<AgentActionResponse> => {
  const response = await apiClient.post<AgentActionResponse>(API_ENDPOINTS.AGENT.ACT, data);
  return response.data;
};



