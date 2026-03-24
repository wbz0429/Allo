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
import type { MarketplaceTool } from "@/core/marketplace/types";

interface InstallDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tool: MarketplaceTool | null;
  onConfirm: (toolId: string, config: Record<string, string>) => void;
  loading?: boolean;
}

export function InstallDialog({
  open,
  onOpenChange,
  tool,
  onConfirm,
  loading,
}: InstallDialogProps) {
  const [values, setValues] = useState<Record<string, string>>({});

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
              No additional configuration needed.
            </DialogDescription>
          </DialogHeader>
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
