export type ToolCategory = "search" | "code" | "data" | "communication";
export type SkillCategory = string;

export interface MarketplaceTool {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  icon: string;
  is_public: boolean;
}

export interface MarketplaceSkill {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  is_public: boolean;
}

export interface OrgInstalledTool {
  id: string;
  tool: MarketplaceTool;
  config_json: string;
  installed_at: string;
}

export interface OrgInstalledSkill {
  id: string;
  skill: MarketplaceSkill;
  installed_at: string;
}

export interface McpConfigField {
  key: string;
  label: string;
  type: "text" | "password";
  required: boolean;
  placeholder?: string;
}
