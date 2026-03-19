export interface Agent {
  name: string;
  description: string;
  model: string | null;
  tool_groups: string[] | null;
  soul?: string | null;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  model?: string | null;
  tool_groups?: string[] | null;
  soul?: string;
}

export interface UpdateAgentRequest {
  description?: string | null;
  model?: string | null;
  tool_groups?: string[] | null;
  soul?: string | null;
}

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  soul_md: string;
  model: string | null;
  tool_groups: string[];
  suggested_skills: string[];
}

export interface CreateAgentFromTemplateRequest {
  template_id: string;
  name?: string;
  description?: string;
  model?: string | null;
  tool_groups?: string[] | null;
}
