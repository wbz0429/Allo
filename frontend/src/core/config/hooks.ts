"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  listModels,
  listToolGroups,
  updateModelsConfig,
  updateToolsConfig,
} from "./api";
import type { ModelsConfig, ToolsConfig } from "./types";

export function useModels() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["config-models"],
    queryFn: () => listModels(),
  });
  return { models: data ?? [], isLoading, error };
}

export function useUpdateModelsConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ModelsConfig) => updateModelsConfig(config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["config-models"] });
      void queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });
}

export function useToolGroups() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["config-tools"],
    queryFn: () => listToolGroups(),
  });
  return { toolGroups: data ?? [], isLoading, error };
}

export function useUpdateToolsConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ToolsConfig) => updateToolsConfig(config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["config-tools"] });
      void queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });
}
