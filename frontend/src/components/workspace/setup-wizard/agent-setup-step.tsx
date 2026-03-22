"use client";

import { BotIcon } from "lucide-react";

interface AgentSetupStepProps {
  onComplete: () => void;
}

export function AgentSetupStep({ onComplete }: AgentSetupStepProps) {
  return (
    <div className="flex flex-col items-center gap-6 py-12">
      <BotIcon className="text-muted-foreground size-12" />
      <div className="text-center">
        <h2 className="text-lg font-semibold">Set Up Agents</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          Create or select agent templates for your team.
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
