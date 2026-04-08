import type { AgentThreadContext } from "../threads";

function normalizeMode(mode: unknown):
  | "autonomous"
  | "precise"
  | "express"
  | undefined {
  if (mode === undefined || mode === null || mode === "") {
    return undefined;
  }

  if (mode === "autonomous" || mode === "precise" || mode === "express") {
    return mode;
  }

  return "autonomous";
}

export const DEFAULT_LOCAL_SETTINGS: LocalSettings = {
  notification: {
    enabled: true,
  },
  context: {
    model_name: undefined,
    mode: undefined,
    reasoning_effort: undefined,
  },
  layout: {
    sidebar_collapsed: false,
  },
};

const LOCAL_SETTINGS_KEY = "allo.local-settings";
const LEGACY_LOCAL_SETTINGS_KEY = "deerflow.local-settings";

export interface LocalSettings {
  notification: {
    enabled: boolean;
  };
  context: Omit<
    AgentThreadContext,
    "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
  > & {
    mode: "autonomous" | "precise" | "express" | undefined;
    reasoning_effort?: "minimal" | "low" | "medium" | "high";
  };
  layout: {
    sidebar_collapsed: boolean;
  };
}

export function getLocalSettings(): LocalSettings {
  if (typeof window === "undefined") {
    return DEFAULT_LOCAL_SETTINGS;
  }
  // Migrate from legacy key
  const legacy = localStorage.getItem(LEGACY_LOCAL_SETTINGS_KEY);
  if (legacy && !localStorage.getItem(LOCAL_SETTINGS_KEY)) {
    localStorage.setItem(LOCAL_SETTINGS_KEY, legacy);
    localStorage.removeItem(LEGACY_LOCAL_SETTINGS_KEY);
  }
  const json = localStorage.getItem(LOCAL_SETTINGS_KEY);
  try {
    if (json) {
      const settings = JSON.parse(json);
      const mergedSettings = {
        ...DEFAULT_LOCAL_SETTINGS,
        context: {
          ...DEFAULT_LOCAL_SETTINGS.context,
          ...settings.context,
          mode: normalizeMode(settings?.context?.mode),
        },
        layout: {
          ...DEFAULT_LOCAL_SETTINGS.layout,
          ...settings.layout,
        },
        notification: {
          ...DEFAULT_LOCAL_SETTINGS.notification,
          ...settings.notification,
        },
      };
      return mergedSettings;
    }
  } catch {}
  return DEFAULT_LOCAL_SETTINGS;
}

export function saveLocalSettings(settings: LocalSettings) {
  localStorage.setItem(LOCAL_SETTINGS_KEY, JSON.stringify(settings));
}
