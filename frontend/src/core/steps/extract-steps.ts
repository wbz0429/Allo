import type { Message } from "@langchain/langgraph-sdk";

import type { Translations } from "../i18n/locales/types";
import {
  extractTextFromMessage,
  hasContent,
  hasPresentFiles,
  hasReasoning,
  hasSubagent,
  hasToolCalls,
} from "../messages/utils";

import type { ExecutionStep, StepStatus } from "./types";

/**
 * Extract a flat list of ExecutionSteps from the message array.
 * Mirrors the grouping logic in `groupMessages` but produces a simpler
 * step-oriented structure for the timeline UI.
 */
export function extractSteps(
  messages: Message[],
  t: Translations,
  isStreaming: boolean,
): ExecutionStep[] {
  const steps: ExecutionStep[] = [];
  let index = 0;

  // Track which tool calls have results
  const toolResults = new Map<string, string>();
  for (const msg of messages) {
    if (msg.type === "tool" && msg.tool_call_id) {
      toolResults.set(msg.tool_call_id, extractTextFromMessage(msg));
    }
  }

  for (const message of messages) {
    if (message.name === "todo_reminder") continue;

    if (message.type === "human") {
      const text = extractTextFromMessage(message);
      steps.push({
        id: message.id ?? `step-${index}`,
        index,
        type: "user_input",
        title: text.length > 40 ? text.slice(0, 40) + "…" : text || "…",
        status: "completed",
        groupId: message.id,
      });
      index++;
      continue;
    }

    if (message.type !== "ai") continue;

    // Subagent tasks
    if (hasSubagent(message)) {
      const taskCalls = message.tool_calls?.filter((tc) => tc.name === "task") ?? [];
      for (const tc of taskCalls) {
        const result = tc.id ? toolResults.get(tc.id) : undefined;
        let status: StepStatus = "in_progress";
        if (result?.startsWith("Task Succeeded")) status = "completed";
        else if (result?.startsWith("Task failed") || result?.startsWith("Task timed out")) status = "failed";
        else if (result !== undefined) status = "in_progress";

        steps.push({
          id: tc.id ?? `step-${index}`,
          index,
          type: "subagent",
          title: (tc.args as Record<string, string>).description ?? t.subtasks.subtask,
          status,
          groupId: message.id,
        });
        index++;
      }
      continue;
    }

    // Present files
    if (hasPresentFiles(message)) {
      steps.push({
        id: message.id ?? `step-${index}`,
        index,
        type: "present_files",
        title: t.toolCalls.presentFiles,
        status: "completed",
        groupId: message.id,
      });
      index++;
      continue;
    }

    // Tool calls (non-subagent, non-present-files)
    if (hasToolCalls(message)) {
      for (const tc of message.tool_calls ?? []) {
        const result = tc.id ? toolResults.get(tc.id) : undefined;
        const status: StepStatus = result !== undefined ? "completed" : "in_progress";
        const toolName = tc.name ?? "tool";

        steps.push({
          id: tc.id ?? `step-${index}`,
          index,
          type: "tool_call",
          title: t.toolCalls.useTool(toolName),
          status,
          groupId: message.id,
        });
        index++;
      }
      continue;
    }

    // Thinking (reasoning only, no content)
    if (hasReasoning(message) && !hasContent(message)) {
      steps.push({
        id: message.id ?? `step-${index}`,
        index,
        type: "thinking",
        title: t.common.thinking,
        status: "completed",
        groupId: message.id,
      });
      index++;
      continue;
    }

    // Final response
    if (hasContent(message)) {
      const isLast = message === messages[messages.length - 1];
      steps.push({
        id: message.id ?? `step-${index}`,
        index,
        type: "response",
        title: truncateText(extractTextFromMessage(message), 40),
        status: isLast && isStreaming ? "in_progress" : "completed",
        groupId: message.id,
      });
      index++;
    }
  }

  return steps;
}

function truncateText(text: string, max: number): string {
  if (!text) return "…";
  return text.length > max ? text.slice(0, max) + "…" : text;
}
