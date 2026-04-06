import type { AIMessage, Message } from "@langchain/langgraph-sdk";
import type { ThreadsClient } from "@langchain/langgraph-sdk/client";
import { useStream } from "@langchain/langgraph-sdk/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";

import { getAPIClient } from "../api";
import { getSession } from "../auth/api";
import { useI18n } from "../i18n/hooks";
import type { FileInMessage } from "../messages/utils";
import type { LocalSettings } from "../settings";
import { useUpdateSubtask } from "../tasks/context";
import type { UploadedFileInfo } from "../uploads";
import { uploadFiles } from "../uploads";

import {
  createThread,
  createThreadRun,
  deleteThread,
  listThreads,
  updateThread,
  updateThreadRun,
} from "./threads-api";
import type { AgentThread, AgentThreadState } from "./types";

export type ToolEndEvent = {
  name: string;
  data: unknown;
};

export type ThreadStreamOptions = {
  threadId?: string | null | undefined;
  context: LocalSettings["context"];
  isMock?: boolean;
  onStart?: (threadId: string) => void;
  onFinish?: (state: AgentThreadState) => void;
  onToolEnd?: (event: ToolEndEvent) => void;
};

export function useThreadStream({
  threadId,
  context,
  isMock,
  onStart,
  onFinish,
  onToolEnd,
}: ThreadStreamOptions) {
  const { t } = useI18n();
  // Track the thread ID that is currently streaming to handle thread changes during streaming
  const [onStreamThreadId, setOnStreamThreadId] = useState(() => threadId);
  // Ref to track current thread ID across async callbacks without causing re-renders,
  // and to allow access to the current thread id in onUpdateEvent
  const threadIdRef = useRef<string | null>(threadId ?? null);
  const startedRef = useRef(false);
  const currentRunIdRef = useRef<string | null>(null);
  const syncedTitleRef = useRef<string | null>(null);

  const listeners = useRef({
    onStart,
    onFinish,
    onToolEnd,
  });

  // Keep listeners ref updated with latest callbacks
  useEffect(() => {
    listeners.current = { onStart, onFinish, onToolEnd };
  }, [onStart, onFinish, onToolEnd]);

  useEffect(() => {
    const normalizedThreadId = threadId ?? null;
    if (!normalizedThreadId) {
      // Just reset for new thread creation when threadId becomes null/undefined
      startedRef.current = false;
      setOnStreamThreadId(normalizedThreadId);
    }
    if (normalizedThreadId) {
      setOnStreamThreadId(normalizedThreadId);
    }
    threadIdRef.current = normalizedThreadId;
    currentRunIdRef.current = null;
    syncedTitleRef.current = null;
  }, [threadId]);

  const _handleOnStart = useCallback((id: string) => {
    if (!startedRef.current) {
      listeners.current.onStart?.(id);
      startedRef.current = true;
    }
  }, []);

  const handleStreamStart = useCallback(
    (_threadId: string) => {
      threadIdRef.current = _threadId;
      _handleOnStart(_threadId);
    },
    [_handleOnStart],
  );
  
  const queryClient = useQueryClient();
  const updateSubtask = useUpdateSubtask();

  const syncThreadTitle = useCallback(
    async (nextTitle: string) => {
      const currentThreadId = threadIdRef.current;
      if (!currentThreadId || syncedTitleRef.current === nextTitle) {
        return;
      }

      syncedTitleRef.current = nextTitle;

      try {
        await updateThread(currentThreadId, { title: nextTitle });
      } catch (error) {
        syncedTitleRef.current = null;
        console.error("Failed to sync thread title:", error);
      }
    },
    [],
  );

  const syncThreadRun = useCallback(
    async (params: Parameters<typeof updateThreadRun>[2]) => {
      const currentThreadId = threadIdRef.current;
      const currentRunId = currentRunIdRef.current;

      if (!currentThreadId || !currentRunId) {
        return;
      }

      try {
        await updateThreadRun(currentThreadId, currentRunId, params);
      } catch (error) {
        console.error("Failed to sync thread run:", error);
      }
    },
    [],
  );

  const thread = useStream<AgentThreadState>({
    client: getAPIClient(isMock),
    assistantId: "lead_agent",
    threadId: onStreamThreadId,
    reconnectOnMount: true,
    fetchStateHistory: { limit: 1 },
    onCreated(meta) {
      handleStreamStart(meta.thread_id);
      setOnStreamThreadId(meta.thread_id);
    },
    onLangChainEvent(event) {
      if (event.event === "on_tool_end") {
        listeners.current.onToolEnd?.({
          name: event.name,
          data: event.data,
        });
      }
    },
    onUpdateEvent(data) {
      const updates: Array<Partial<AgentThreadState> | null> = Object.values(
        data || {},
      );
      for (const update of updates) {
        if (update && "title" in update && update.title) {
          void syncThreadTitle(update.title);
          void queryClient.setQueriesData(
            {
              queryKey: ["threads", "search"],
              exact: false,
            },
            (oldData: Array<AgentThread> | undefined) => {
              return oldData?.map((t) => {
                if (t.thread_id === threadIdRef.current) {
                  return {
                    ...t,
                    values: {
                      ...t.values,
                      title: update.title,
                    },
                  };
                }
                return t;
              });
            },
          );
        }
      }
    },
    onCustomEvent(event: unknown) {
      if (
        typeof event === "object" &&
        event !== null &&
        "type" in event &&
        event.type === "task_running"
      ) {
        const e = event as {
          type: "task_running";
          task_id: string;
          message: AIMessage;
        };
        updateSubtask({ id: e.task_id, latestMessage: e.message });
      }
    },
    onFinish(state) {
      void syncThreadRun({
        status: "completed",
        finished_at: new Date().toISOString(),
      });
      currentRunIdRef.current = null;
      listeners.current.onFinish?.(state.values);
      void queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
    },
  });

  // Optimistic messages shown before the server stream responds
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);
  // Track message count before sending so we know when server has responded
  const prevMsgCountRef = useRef(thread.messages.length);

  // Clear optimistic when server messages arrive (count increases)
  useEffect(() => {
    if (
      optimisticMessages.length > 0 &&
      thread.messages.length > prevMsgCountRef.current
    ) {
      setOptimisticMessages([]);
    }
  }, [thread.messages.length, optimisticMessages.length]);

  const sendMessage = useCallback(
    async (
      threadId: string,
      message: PromptInputMessage,
      extraContext?: Record<string, unknown>,
    ) => {
      const text = message.text.trim();

      // Capture current count before showing optimistic messages
      prevMsgCountRef.current = thread.messages.length;

      // Build optimistic files list with uploading status
      const optimisticFiles: FileInMessage[] = (message.files ?? []).map(
        (f) => ({
          filename: f.filename ?? "",
          size: 0,
          status: "uploading" as const,
        }),
      );

      // Create optimistic human message (shown immediately)
      const optimisticKwargs: Record<string, unknown> = {};
      if (optimisticFiles.length > 0) {
        optimisticKwargs.files = optimisticFiles;
      }
      if (message.knowledgeBases && message.knowledgeBases.length > 0) {
        optimisticKwargs.knowledge_bases = message.knowledgeBases;
      }

      const optimisticHumanMsg: Message = {
        type: "human",
        id: `opt-human-${Date.now()}`,
        content: text ? [{ type: "text", text }] : "",
        additional_kwargs: optimisticKwargs,
      };

      const newOptimistic: Message[] = [optimisticHumanMsg];
      if (optimisticFiles.length > 0) {
        // Mock AI message while files are being uploaded
        newOptimistic.push({
          type: "ai",
          id: `opt-ai-${Date.now()}`,
          content: t.uploads.uploadingFiles,
          additional_kwargs: { element: "task" },
        });
      }
      setOptimisticMessages(newOptimistic);

      let uploadedFileInfo: UploadedFileInfo[] = [];
      const gatewayThreadId = threadId;
      let sessionUserId: string | undefined;
      let sessionOrgId: string | undefined;

      try {
        if (!gatewayThreadId) {
          throw new Error("Thread is not ready.");
        }

        await createThread({
          thread_id: gatewayThreadId,
          agent_name:
            typeof extraContext?.agent_name === "string"
              ? extraContext.agent_name
              : typeof context.agent_name === "string"
                ? context.agent_name
                : undefined,
          default_model: context.model_name as string | undefined,
          last_model_name: context.model_name as string | undefined,
          status: "active",
        });

        threadIdRef.current = gatewayThreadId;

        const run = await createThreadRun(gatewayThreadId, {
          model_name: context.model_name as string | undefined,
          agent_name:
            typeof extraContext?.agent_name === "string"
              ? extraContext.agent_name
              : typeof context.agent_name === "string"
                ? context.agent_name
                : undefined,
          status: "running",
        });

        sessionUserId = run.user_id;
        sessionOrgId = run.org_id;

        try {
          if (!sessionUserId || !sessionOrgId) {
            const sessionResult = await getSession();
            sessionUserId = sessionResult.data?.user_id;
            sessionOrgId = sessionResult.data?.org_id;
          }
        } catch {}

        if (!sessionUserId || !sessionOrgId) {
          throw new Error("Failed to load session context for LangGraph run.");
        }

        currentRunIdRef.current = run.id;

        // Upload files first if any
        if (message.files && message.files.length > 0) {
          try {
            // Convert FileUIPart to File objects by fetching blob URLs
            const filePromises = message.files.map(async (fileUIPart) => {
              if (fileUIPart.url && fileUIPart.filename) {
                try {
                  // Fetch the blob URL to get the file data
                  const response = await fetch(fileUIPart.url);
                  const blob = await response.blob();

                  // Create a File object from the blob
                  return new File([blob], fileUIPart.filename, {
                    type: fileUIPart.mediaType || blob.type,
                  });
                } catch (error) {
                  console.error(
                    `Failed to fetch file ${fileUIPart.filename}:`,
                    error,
                  );
                  return null;
                }
              }
              return null;
            });

            const conversionResults = await Promise.all(filePromises);
            const files = conversionResults.filter(
              (file): file is File => file !== null,
            );
            const failedConversions = conversionResults.length - files.length;

            if (failedConversions > 0) {
              throw new Error(
                `Failed to prepare ${failedConversions} attachment(s) for upload. Please retry.`,
              );
            }

            if (!gatewayThreadId) {
              throw new Error("Thread is not ready for file upload.");
            }

            if (files.length > 0) {
              const uploadResponse = await uploadFiles(gatewayThreadId, files);
              uploadedFileInfo = uploadResponse.files;

              // Update optimistic human message with uploaded status + paths
              const uploadedFiles: FileInMessage[] = uploadedFileInfo.map(
                (info) => ({
                  filename: info.filename,
                  size: info.size,
                  path: info.virtual_path,
                  status: "uploaded" as const,
                }),
              );
              setOptimisticMessages((messages) => {
                if (messages.length > 1 && messages[0]) {
                  const humanMessage: Message = messages[0];
                  return [
                    {
                      ...humanMessage,
                      additional_kwargs: { files: uploadedFiles },
                    },
                    ...messages.slice(1),
                  ];
                }
                return messages;
              });
            }
          } catch (error) {
            console.error("Failed to upload files:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to upload files.";
            toast.error(errorMessage);
            setOptimisticMessages([]);
            throw error;
          }
        }

        // Build files metadata for submission (included in additional_kwargs)
        const filesForSubmit: FileInMessage[] = uploadedFileInfo.map(
          (info) => ({
            filename: info.filename,
            size: info.size,
            path: info.virtual_path,
            status: "uploaded" as const,
          }),
        );

        const additionalKwargs: Record<string, unknown> = {};
        if (filesForSubmit.length > 0) {
          additionalKwargs.files = filesForSubmit;
        }
        if (message.knowledgeBases && message.knowledgeBases.length > 0) {
          additionalKwargs.knowledge_bases = message.knowledgeBases;
        }

        const input: Partial<AgentThreadState> = {
          messages: [
            {
              type: "human" as const,
              content: [
                {
                  type: "text" as const,
                  text,
                },
              ],
              additional_kwargs: additionalKwargs,
            },
          ],
        };

        const runContext = {
          ...extraContext,
          ...context,
          user_id: sessionUserId,
          org_id: sessionOrgId,
          thinking_enabled: context.mode !== "flash",
          is_plan_mode: context.mode === "pro" || context.mode === "ultra",
          subagent_enabled: context.mode === "ultra",
          thread_id: gatewayThreadId,
          kb_ids: message.knowledgeBases?.map((kb) => kb.id),
        };

        await thread.submit(input, {
          threadId: threadId,
          streamSubgraphs: true,
          streamResumable: true,
          context: runContext,
          config: { recursion_limit: 150 },
        });
        void queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
      } catch (error) {
        const finishedAt = new Date().toISOString();
        if (currentRunIdRef.current) {
          void syncThreadRun({
            status: "failed",
            finished_at: finishedAt,
            error_message: error instanceof Error ? error.message : "Unknown error",
          });
          currentRunIdRef.current = null;
        }
        setOptimisticMessages([]);
        throw error;
      }
    },
    [
      thread,
      t.uploads.uploadingFiles,
      context,
      queryClient,
      syncThreadRun,
    ],
  );

  // Merge thread with optimistic messages for display
  const mergedThread =
    optimisticMessages.length > 0
      ? ({
          ...thread,
          messages: [...thread.messages, ...optimisticMessages],
        } as typeof thread)
      : thread;

  return [mergedThread, sendMessage, onStreamThreadId] as const;
}

export function useThreads(
  params: Parameters<ThreadsClient["search"]>[0] = {
    limit: 50,
    sortBy: "updated_at",
    sortOrder: "desc",
    select: ["thread_id", "updated_at", "values"],
  },
) {
  return useQuery<AgentThread[]>({
    queryKey: ["threads", "search", params],
    queryFn: async () => listThreads(),
    refetchOnWindowFocus: false,
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ threadId }: { threadId: string }) => {
      await deleteThread(threadId);
    },
    onSuccess(_, { threadId }) {
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread>) => {
          return oldData.filter((t) => t.thread_id !== threadId);
        },
      );
    },
  });
}

export function useRenameThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      threadId,
      title,
    }: {
      threadId: string;
      title: string;
    }) => {
      await updateThread(threadId, { title });
    },
    onSuccess(_, { threadId, title }) {
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread>) => {
          return oldData.map((t) => {
            if (t.thread_id === threadId) {
              return {
                ...t,
                values: {
                  ...t.values,
                  title,
                },
              };
            }
            return t;
          });
        },
      );
    },
  });
}
