"use client";

import {
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CircleDotIcon,
  Loader2Icon,
  MessageSquareIcon,
  SearchIcon,
  SparklesIcon,
  UserIcon,
  WrenchIcon,
  XCircleIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSteps } from "@/core/steps/context";
import type { ExecutionStep, StepStatus, StepType } from "@/core/steps/types";
import { cn } from "@/lib/utils";

function stepIcon(type: StepType) {
  switch (type) {
    case "user_input":
      return UserIcon;
    case "thinking":
      return SparklesIcon;
    case "tool_call":
      return WrenchIcon;
    case "subagent":
      return SearchIcon;
    case "response":
      return MessageSquareIcon;
    case "clarification":
      return MessageSquareIcon;
    case "present_files":
      return CircleDotIcon;
  }
}

function statusColor(status: StepStatus) {
  switch (status) {
    case "pending":
      return "bg-muted-foreground/30";
    case "in_progress":
      return "bg-blue-500";
    case "completed":
      return "bg-emerald-500";
    case "failed":
      return "bg-red-500";
  }
}

function StatusIndicator({ status }: { status: StepStatus }) {
  if (status === "in_progress") {
    return <Loader2Icon className="size-3 animate-spin text-blue-500" />;
  }
  if (status === "completed") {
    return <CheckCircleIcon className="size-3 text-emerald-500" />;
  }
  if (status === "failed") {
    return <XCircleIcon className="size-3 text-red-500" />;
  }
  return <div className={cn("size-2 rounded-full", statusColor(status))} />;
}

function StepDot({
  step,
  isActive,
  onClick,
}: {
  step: ExecutionStep;
  isActive: boolean;
  onClick: () => void;
}) {
  const Icon = stepIcon(step.type);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className={cn(
            "relative flex shrink-0 items-center justify-center rounded-full transition-all",
            "size-7 hover:bg-muted",
            isActive && "ring-primary/50 bg-muted ring-2",
          )}
        >
          <Icon className={cn("size-3.5", isActive ? "text-foreground" : "text-muted-foreground")} />
          <span className="absolute -bottom-0.5 -right-0.5">
            <StatusIndicator status={step.status} />
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[240px] text-xs">
        {step.title}
      </TooltipContent>
    </Tooltip>
  );
}

export function StepTimeline({
  className,
  onScrollToStep,
}: {
  className?: string;
  onScrollToStep?: (groupId: string) => void;
}) {
  const { steps, activeStepId, setActiveStepId, goToStep } = useSteps();
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeIndex = steps.findIndex((s) => s.id === activeStepId);

  // Auto-scroll the timeline bar to keep the active dot visible
  useEffect(() => {
    if (!scrollRef.current || activeIndex < 0) return;
    const container = scrollRef.current;
    const dot = container.children[activeIndex] as HTMLElement | undefined;
    if (dot) {
      dot.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, [activeIndex]);

  const handleStepClick = useCallback(
    (step: ExecutionStep) => {
      setActiveStepId(step.id);
      if (step.groupId && onScrollToStep) {
        onScrollToStep(step.groupId);
      }
    },
    [setActiveStepId, onScrollToStep],
  );

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goToStep("prev");
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goToStep("next");
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToStep]);

  if (steps.length < 3) return null;

  return (
    <div
      className={cn(
        "bg-background/80 flex items-center gap-1 rounded-lg border px-2 py-1.5 backdrop-blur-sm",
        className,
      )}
    >
      <Button
        variant="ghost"
        size="icon"
        className="size-6 shrink-0"
        disabled={activeIndex <= 0}
        onClick={() => goToStep("prev")}
      >
        <ChevronLeftIcon className="size-3.5" />
      </Button>

      <div
        ref={scrollRef}
        className="flex items-center gap-0.5 overflow-x-auto scrollbar-none"
      >
        {steps.map((step) => (
          <StepDot
            key={step.id}
            step={step}
            isActive={step.id === activeStepId}
            onClick={() => handleStepClick(step)}
          />
        ))}
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="size-6 shrink-0"
        disabled={activeIndex >= steps.length - 1}
        onClick={() => goToStep("next")}
      >
        <ChevronRightIcon className="size-3.5" />
      </Button>

      <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
        {activeIndex >= 0 ? activeIndex + 1 : "–"}/{steps.length}
      </span>
    </div>
  );
}
