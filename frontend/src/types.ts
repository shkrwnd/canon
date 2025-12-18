export interface User {
  id: number;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface Module {
  id: number;
  user_id: number;
  name: string;
  standing_instruction: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: number;
  user_id: number;
  module_id: number | null;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  role: MessageRole;
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserRegister {
  email: string;
  password: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface ModuleCreate {
  name: string;
  standing_instruction?: string;
  content?: string;
}

export interface ModuleUpdate {
  name?: string;
  standing_instruction?: string;
  content?: string;
}

export interface ChatCreate {
  module_id?: number | null;
  title?: string | null;
}

export interface ChatMessageCreate {
  content: string;
  role: MessageRole;
  metadata?: Record<string, any>;
}

export interface AgentActionRequest {
  message: string;
  module_id?: number | null;
  chat_id?: number | null;
}

export interface AgentActionResponse {
  module: Module | null;
  chat_message: ChatMessage;
  agent_decision: Record<string, any>;
  web_search_performed: boolean;
}



