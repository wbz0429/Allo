import { getBackendBaseURL } from "../config";

import type { AgentThread } from "./types";

type ThreadRecord = AgentThread;

export interface CreateThreadParams {
  thread_id?: string;
  title?: string;
  agent_name?: string;
  default_model?: string;
  last_model_name?: string;
  status?: string;
}

export interface UpdateThreadParams {
  title?: string;
  agent_name?: string;
  default_model?: string;
  last_model_name?: string;
  status?: string;
  last_active_at?: string;
}

export interface ThreadRunRecord {
  id: string;
  thread_id?: string;
  user_id?: string;
  org_id?: string;
  model_name?: string;
  agent_name?: string;
  sandbox_id?: string;
  status?: string;
  started_at?: string;
  finished_at?: string;
  error_message?: string | null;
}

export interface CreateThreadRunParams {
  model_name?: string;
  agent_name?: string;
  sandbox_id?: string;
  status?: string;
}

export interface UpdateThreadRunParams {
  model_name?: string;
  agent_name?: string;
  sandbox_id?: string;
  status?: string;
  finished_at?: string;
  error_message?: string | null;
}

async function readErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  const error = await response
    .json()
    .catch(() => ({ detail: fallback }));

  if (typeof error?.detail === "string") {
    return error.detail;
  }

  return fallback;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  fallbackError = "Request failed",
): Promise<T> {
  const response = await fetch(`${getBackendBaseURL()}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, fallbackError));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function createThread(
  params: CreateThreadParams,
): Promise<ThreadRecord> {
  return request<ThreadRecord>(
    "/api/threads",
    {
      method: "POST",
      body: JSON.stringify(params),
    },
    "Failed to create thread",
  );
}

export async function listThreads(): Promise<ThreadRecord[]> {
  return request<ThreadRecord[]>(
    "/api/threads",
    undefined,
    "Failed to list threads",
  );
}

export async function deleteThread(id: string): Promise<void> {
  await request<void>(
    `/api/threads/${id}`,
    {
      method: "DELETE",
    },
    "Failed to delete thread",
  );
}

export async function updateThread(
  id: string,
  params: UpdateThreadParams,
): Promise<ThreadRecord> {
  return request<ThreadRecord>(
    `/api/threads/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(params),
    },
    "Failed to update thread",
  );
}

export async function createThreadRun(
  threadId: string,
  params: CreateThreadRunParams,
): Promise<ThreadRunRecord> {
  return request<ThreadRunRecord>(
    `/api/threads/${threadId}/runs`,
    {
      method: "POST",
      body: JSON.stringify(params),
    },
    "Failed to create thread run",
  );
}

export async function updateThreadRun(
  threadId: string,
  runId: string,
  params: UpdateThreadRunParams,
): Promise<ThreadRunRecord> {
  return request<ThreadRunRecord>(
    `/api/threads/${threadId}/runs/${runId}`,
    {
      method: "PATCH",
      body: JSON.stringify(params),
    },
    "Failed to update thread run",
  );
}
