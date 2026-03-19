"use client";

import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

import type { McpConfigField, MarketplaceTool } from "@/core/marketplace/types";

interface InstallDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tool: MarketplaceTool | null;
  onConfirm: (toolId: string, config: Record<string, string>) => void;
  loading?: boolean;
}

function parseConfigFields(mcpConfigJson: string): McpConfigField[] {
  try {
    const parsed = JSON.parse(mcpConfigJson) as Record<string, unknown>;
    const env = (parsed.env ?? {}) as Record<string, string>;
    return Object.keys(env).map((key) => ({
      key,
      label: key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
      type: key.toLowerCase().includes("key") ||
        key.toLowerCase().includes("secret") ||
        key.toLowerCase().includes("token")
        ? ("password" as const)
        : ("text" as const),
      required: true,
      placeholder: env[key] || `Enter ${key}`,
    }));
  } catch {
    return [];
  }
}

export function InstallDialog({
  open,
  onOpenChange,
  tool,
  onConfirm,
  loading,
}: InstallDialogProps) {
  const [values, setValues] = useState<Record<string, string>>({});

  const fields = tool ? parseConfigFields(tool.mcp_config_json) : [];

  const handleChange = useCallback((key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!tool) return;
      onConfirm(tool.id, values);
      setValues({});
    },
    [tool, values, onConfirm],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              Install {tool?.name}
            </DialogTitle>
            <DialogDescription>
              {fields.length > 0
                ? "Configure the required settings to install this tool."
                : "No additional configuration needed."}
            </DialogDescription>
          </DialogHeader>
          {fields.length > 0 && (
            <div className="mt-4 flex flex-col gap-3">
              {fields.map((field) => (
                <div key={field.key} className="flex flex-col gap-1.5">
                  <label
                    htmlFor={`install-field-${field.key}`}
                    className="text-sm font-medium"
                  >
                    {field.label}
                    {field.required && (
                      <span className="text-destructive ml-0.5">*</span>
                    )}
                  </label>
                  <Input
                    id={`install-field-${field.key}`}
                    type={field.type}
                    placeholder={field.placeholder}
                    required={field.required}
                    value={values[field.key] ?? ""}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                  />
                </div>
              ))}
            </div>
          )}
          <DialogFooter className="mt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Installing…" : "Install"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
