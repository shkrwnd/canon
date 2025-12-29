export interface Document {
  id: number;
  user_id: number;
  project_id: number;
  name: string;
  standing_instruction: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreate {
  name: string;
  standing_instruction?: string;
  content?: string;
  project_id: number;
}

export interface DocumentUpdate {
  name?: string;
  standing_instruction?: string;
  content?: string;
}



