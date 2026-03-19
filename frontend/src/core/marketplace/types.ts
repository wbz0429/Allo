export type ToolCategory = "search" | "code" | "data" | "communication";
export type SkillCategory = string;

export interface MarketplaceTool {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  icon: string;
  mcp_config_json: string;
  is_public: boolean;
  created_at: string;
}

export interface MarketplaceSkill {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  skill_content: string;
  is_public: boolean;
  created_at: string;
}

export interface OrgInstalledTool {
  id: string;
  org_id: string;
  tool_id: string;
  config_json: string;
  installed_at: string;
}

export interface OrgInstalledSkill {
  id: string;
  org_id: string;
  skill_id: string;
  installed_at: string;
}

export interface McpConfigField {
  key: string;
  label: string;
  type: "text" | "password";
  required: boolean;
  placeholder?: string;
}
