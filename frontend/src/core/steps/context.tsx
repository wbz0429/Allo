"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { areStepsEqual } from "./equality";
import type { ExecutionStep } from "./types";

interface StepContextValue {
  steps: ExecutionStep[];
  setSteps: (steps: ExecutionStep[]) => void;
  activeStepId: string | null;
  setActiveStepId: (id: string | null) => void;
  goToStep: (direction: "prev" | "next") => void;
}

const StepContext = createContext<StepContextValue | null>(null);

export function StepProvider({ children }: { children: ReactNode }) {
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [activeStepId, setActiveStepId] = useState<string | null>(null);

  const handleSetSteps = useCallback((nextSteps: ExecutionStep[]) => {
    setSteps((currentSteps) =>
      areStepsEqual(currentSteps, nextSteps) ? currentSteps : nextSteps,
    );
    setActiveStepId((currentActiveStepId) => {
      if (!currentActiveStepId) return currentActiveStepId;
      return nextSteps.some((step) => step.id === currentActiveStepId)
        ? currentActiveStepId
        : null;
    });
  }, []);

  const goToStep = useCallback(
    (direction: "prev" | "next") => {
      if (steps.length === 0) return;
      const currentIndex = steps.findIndex((s) => s.id === activeStepId);
      let nextIndex: number;
      if (currentIndex === -1) {
        nextIndex = direction === "next" ? 0 : steps.length - 1;
      } else {
        nextIndex =
          direction === "next"
            ? Math.min(currentIndex + 1, steps.length - 1)
            : Math.max(currentIndex - 1, 0);
      }
      const step = steps[nextIndex];
      if (step) setActiveStepId(step.id);
    },
    [steps, activeStepId],
  );

  const value = useMemo(
    () => ({ steps, setSteps: handleSetSteps, activeStepId, setActiveStepId, goToStep }),
    [steps, handleSetSteps, activeStepId, goToStep],
  );

  return <StepContext value={value}>{children}</StepContext>;
}

const NOOP_STEPS: StepContextValue = {
  steps: [],
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setSteps: () => {},
  activeStepId: null,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setActiveStepId: () => {},
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  goToStep: () => {},
};

export function useSteps() {
  const ctx = useContext(StepContext);
  return ctx ?? NOOP_STEPS;
}
