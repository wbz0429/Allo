import type { Message } from "@langchain/langgraph-sdk";

import { Shimmer } from "@/components/ai-elements/shimmer";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

export type StreamingPhase =
  | "connecting"
  | "thinking"
  | "executing"
  | "generating";

/**
 * Infer the current streaming phase from the latest messages.
 * Called only when `isLoading` is true.
 */
export function inferStreamingPhase(
  messages: Message[],
  hasOptimistic: boolean,
): StreamingPhase {
  // Walk backwards to find the latest AI message
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (!msg) continue;

    if (msg.type === "ai") {
      // Has tool calls → executing
      const toolCalls = (msg as Record<string, unknown>).tool_calls as
        | unknown[]
        | undefined;
      if (toolCalls && toolCalls.length > 0) {
        return "executing";
      }

      // Has text content → generating
      const content = msg.content;
      if (typeof content === "string" && content.length > 0) {
        return "generating";
      }
      if (Array.isArray(content)) {
        const hasText = content.some(
          (c) =>
            typeof c === "object" &&
            c !== null &&
            "type" in c &&
            c.type === "text" &&
            "text" in c &&
            typeof c.text === "string" &&
            c.text.length > 0,
        );
        if (hasText) return "generating";
      }

      // AI message exists but empty → thinking
      return "thinking";
    }
  }

  // No AI message yet — still connecting (or optimistic message showing)
  return hasOptimistic ? "connecting" : "thinking";
}

export function StreamingStatus({
  className,
  phase,
}: {
  className?: string;
  phase: StreamingPhase;
}) {
  const { t } = useI18n();

  const label = t.streaming[phase];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex">
        <div className="mx-0.5 size-1.5 animate-bouncing rounded-full bg-[#a3a1a1] opacity-100" />
        <div className="mx-0.5 size-1.5 animate-bouncing rounded-full bg-[#a3a1a1] opacity-100 [animation-delay:0.2s]" />
        <div className="mx-0.5 size-1.5 animate-bouncing rounded-full bg-[#a3a1a1] opacity-100 [animation-delay:0.4s]" />
      </div>
      <Shimmer
        className="text-muted-foreground text-sm"
        duration={2}
        spread={2}
      >
        {label}
      </Shimmer>
    </div>
  );
}
