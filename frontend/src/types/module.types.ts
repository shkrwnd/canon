export interface Module {
  id: number;
  user_id: number;
  name: string;
  standing_instruction: string;
  content: string;
  created_at: string;
  updated_at: string;
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

