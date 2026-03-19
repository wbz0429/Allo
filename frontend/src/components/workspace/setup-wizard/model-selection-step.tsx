"use client";

import { CheckIcon, CpuIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { useModels, useUpdateModelsConfig } from "@/core/config/hooks";
import { cn } from "@/lib/utils";

interface ModelSelectionStepProps {
  onComplete: () => void;
}

export function ModelSelectionStep({ onComplete }: ModelSelectionStepProps) {
  const { models, isLoading } = useModels();
  const updateConfig = useUpdateModelsConfig();

  const [enabledModels, setEnabledModels] = useState<Set<string>>(new Set());
  const [defaultModel, setDefaultModel] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Initialize from loaded models — pick all as enabled by default
  if (!initialized && models.length > 0) {
    setEnabledModels(new Set(models.map((m) => m.id)));
    setDefaultModel(models[0]?.id ?? null);
    setInitialized(true);
  }

  const toggleModel = useCallback((modelId: string) => {
    setEnabledModels((prev) => {
      const next = new Set(prev);
      if (next.has(modelId)) {
        next.delete(modelId);
      } else {
        next.add(modelId);
      }
      return next;
    });
  }, []);

  const handleSetDefault = useCallback((modelId: string) => {
    setDefaultModel(modelId);
    setEnabledModels((prev) => new Set([...prev, modelId]));
  }, []);

  const handleSave = useCallback(async () => {
    try {
      await updateConfig.mutateAsync({
        default_model: defaultModel,
        enabled_models: [...enabledModels],
      });
      toast.success("Model configuration saved");
      onComplete();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    }
  }, [defaultModel, enabledModels, onComplete, updateConfig]);

  if (isLoading) {
    return (
      <div className="text-muted-foreground flex h-40 items-center justify-center text-sm">
        Loading models…
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Select Models</h2>
          <p className="text-muted-foreground text-sm">
            Choose which AI models are available in your workspace
          </p>
        </div>
        <div className="text-muted-foreground flex h-40 flex-col items-center justify-center gap-2 rounded-lg border border-dashed">
          <CpuIcon className="size-8 opacity-50" />
          <p className="text-sm">No models available yet</p>
          <p className="text-xs">Models will appear once the backend is configured</p>
        </div>
        <div className="flex justify-end">
          <Button onClick={onComplete}>Continue</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Select Models</h2>
        <p className="text-muted-foreground text-sm">
          Choose which AI models are available in your workspace and set a
          default
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {models.map((model) => {
          const isEnabled = enabledModels.has(model.id);
          const isDefault = defaultModel === model.id;
          return (
            <Card
              key={model.id}
              className={cn(
                "relative transition-shadow",
                isEnabled && "ring-primary/30 ring-2",
                isDefault && "ring-primary ring-2",
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-lg">
                      <CpuIcon className="size-5" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="text-sm">{model.name}</CardTitle>
                      <p className="text-muted-foreground text-xs">
                        {model.provider}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={isEnabled}
                    onCheckedChange={() => toggleModel(model.id)}
                    aria-label={`Enable ${model.name}`}
                  />
                </div>
              </CardHeader>
              {model.description && (
                <CardContent className="pt-0 pb-3">
                  <CardDescription className="line-clamp-2 text-xs">
                    {model.description}
                  </CardDescription>
                </CardContent>
              )}
              <CardContent className="pt-0">
                <Button
                  size="sm"
                  variant={isDefault ? "default" : "outline"}
                  className="w-full text-xs"
                  disabled={!isEnabled}
                  onClick={() => handleSetDefault(model.id)}
                >
                  {isDefault && <CheckIcon className="mr-1 size-3" />}
                  {isDefault ? "Default" : "Set as default"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={updateConfig.isPending}>
          {updateConfig.isPending ? "Saving…" : "Save & Continue"}
        </Button>
      </div>
    </div>
  );
}
