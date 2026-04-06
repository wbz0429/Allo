import type { ExecutionStep } from "./types";

export function areStepsEqual(
  prev: ExecutionStep[],
  next: ExecutionStep[],
): boolean {
  if (prev === next) return true;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    const prevStep = prev[i];
    const nextStep = next[i];

    if (!prevStep || !nextStep) return false;
    if (prevStep.id !== nextStep.id) return false;
    if (prevStep.index !== nextStep.index) return false;
    if (prevStep.type !== nextStep.type) return false;
    if (prevStep.title !== nextStep.title) return false;
    if (prevStep.status !== nextStep.status) return false;
    if (prevStep.groupId !== nextStep.groupId) return false;
  }

  return true;
}
