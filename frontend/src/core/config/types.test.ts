import { describe, it, expect } from "vitest";

describe("config types", () => {
  it("TenantConfig has expected shape", () => {
    const config: import("./types").TenantConfig = {
      default_model: "gpt-4o",
      enabled_models: ["gpt-4o"],
      enabled_tool_groups: ["search"],
      custom_settings: {},
    };
    expect(config.default_model).toBe("gpt-4o");
    expect(config.enabled_models).toHaveLength(1);
  });

  it("ModelInfo has expected shape", () => {
    const model: import("./types").ModelInfo = {
      id: "gpt-4o",
      name: "GPT-4o",
      provider: "openai",
      description: "OpenAI GPT-4o",
    };
    expect(model.id).toBe("gpt-4o");
    expect(model.provider).toBe("openai");
  });

  it("ToolGroupInfo has expected shape", () => {
    const tg: import("./types").ToolGroupInfo = {
      id: "search",
      name: "Search Tools",
      tools: ["tavily", "duckduckgo"],
    };
    expect(tg.tools).toHaveLength(2);
  });

  it("ModelsConfig has expected shape", () => {
    const mc: import("./types").ModelsConfig = {
      default_model: "gpt-4o",
      enabled_models: ["gpt-4o", "claude-3"],
    };
    expect(mc.enabled_models).toHaveLength(2);
  });

  it("ToolsConfig has expected shape", () => {
    const tc: import("./types").ToolsConfig = {
      enabled_tool_groups: ["search"],
    };
    expect(tc.enabled_tool_groups).toHaveLength(1);
  });
});
