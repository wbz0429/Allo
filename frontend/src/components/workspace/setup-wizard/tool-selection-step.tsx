"use client";

import { WrenchIcon } from "lucide-react";

interface ToolSelectionStepProps {
  onComplete: () => void;
}

export function ToolSelectionStep({ onComplete }: ToolSelectionStepProps) {
  return (
    <div className="flex flex-col items-center gap-6 py-12">
      <WrenchIcon className="text-muted-foreground size-12" />
      <div className="text-center">
        <h2 className="text-lg font-semibold">Select Tools</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          Choose which tool groups to enable for your workspace.
        </p>
      </div>
      <button
        type="button"
        onClick={onComplete}
        className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium"
      >
        Continue
      </button>
    </div>
  );
}
