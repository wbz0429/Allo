export type StepStatus = "pending" | "in_progress" | "completed" | "failed";

export type StepType =
  | "user_input"
  | "thinking"
  | "tool_call"
  | "subagent"
  | "response"
  | "clarification"
  | "present_files";

export interface ExecutionStep {
  id: string;
  index: number;
  type: StepType;
  title: string;
  status: StepStatus;
  /** Message group id — used to scroll to the corresponding DOM element */
  groupId: string | undefined;
}
