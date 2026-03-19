export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description?: string;
}

export interface ToolGroupInfo {
  id: string;
  name: string;
  description?: string;
  tools: string[];
}

export interface TenantConfig {
  default_model: string | null;
  enabled_models: string[];
  enabled_tool_groups: string[];
  custom_settings: Record<string, unknown>;
}

export interface ModelsConfig {
  default_model: string | null;
  enabled_models: string[];
}

export interface ToolsConfig {
  enabled_tool_groups: string[];
}
