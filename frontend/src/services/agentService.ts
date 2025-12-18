import apiClient from "../clients/apiClient";
import { API_ENDPOINTS } from "../utils/constants";
import { AgentActionRequest, AgentActionResponse } from "../types";

export const agentAction = async (data: AgentActionRequest): Promise<AgentActionResponse> => {
  const response = await apiClient.post<AgentActionResponse>(API_ENDPOINTS.AGENT.ACT, data);
  return response.data;
};



