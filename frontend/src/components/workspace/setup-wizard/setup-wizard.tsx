"use client";

import {
  BotIcon,
  CheckCircle2Icon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CpuIcon,
  WrenchIcon,
} from "lucide-react";
import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

import { AgentSetupStep } from "./agent-setup-step";
import { CompletionStep } from "./completion-step";
import { ModelSelectionStep } from "./model-selection-step";
import { ToolSelectionStep } from "./tool-selection-step";

const STEPS = [
  { id: "models", label: "Models", icon: CpuIcon },
  { id: "tools", label: "Tools", icon: WrenchIcon },
  { id: "agents", label: "Agents", icon: BotIcon },
  { id: "done", label: "Done", icon: CheckCircle2Icon },
] as const;

type StepId = (typeof STEPS)[number]["id"];

export function SetupWizard() {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());

  const step = STEPS[currentStep]!;
  const progress = ((currentStep + 1) / STEPS.length) * 100;
  const isFirst = currentStep === 0;
  const isLast = currentStep === STEPS.length - 1;

  const markComplete = useCallback(
    (stepId: StepId) => {
      setCompletedSteps((prev) => new Set([...prev, stepId]));
    },
    [],
  );

  const goNext = useCallback(() => {
    markComplete(step.id);
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  }, [markComplete, step.id]);

  const goPrev = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  }, []);

  return (
    <div className="flex size-full flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold">Setup Wizard</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          Configure your workspace in a few steps
        </p>
      </div>

      {/* Step indicator */}
      <div className="border-b px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <div className="mb-3 flex items-center justify-between">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const isActive = i === currentStep;
              const isDone = completedSteps.has(s.id);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    if (i < currentStep || isDone) setCurrentStep(i);
                  }}
                  disabled={i > currentStep && !isDone}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : isDone
                        ? "text-primary hover:bg-primary/10 cursor-pointer"
                        : "text-muted-foreground cursor-default",
                  )}
                >
                  <Icon className="size-4" />
                  <span className="hidden sm:inline">{s.label}</span>
                </button>
              );
            })}
          </div>
          <Progress value={progress} className="h-1.5" />
        </div>
      </div>

      {/* Step content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl">
          {step.id === "models" && <ModelSelectionStep onComplete={goNext} />}
          {step.id === "tools" && <ToolSelectionStep onComplete={goNext} />}
          {step.id === "agents" && <AgentSetupStep onComplete={goNext} />}
          {step.id === "done" && <CompletionStep />}
        </div>
      </div>

      {/* Footer navigation */}
      {!isLast && (
        <div className="flex items-center justify-between border-t px-6 py-4">
          <Button
            variant="outline"
            onClick={goPrev}
            disabled={isFirst}
          >
            <ChevronLeftIcon className="mr-1.5 size-4" />
            Back
          </Button>
          <Button variant="ghost" onClick={goNext}>
            Skip
            <ChevronRightIcon className="ml-1.5 size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
