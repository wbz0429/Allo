import { getBackendBaseURL } from "@/core/config";

import type {
  CreateKnowledgeBaseRequest,
  KnowledgeBase,
  KnowledgeDocument,
  SearchResult,
  UpdateKnowledgeBaseRequest,
} from "./types";

const BASE = () => `${getBackendBaseURL()}/api/knowledge-bases`;

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await fetch(BASE(), { credentials: "include" });
  if (!res.ok)
    throw new Error(`Failed to load knowledge bases: ${res.statusText}`);
  return res.json() as Promise<KnowledgeBase[]>;
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const res = await fetch(`${BASE()}/${id}`, { credentials: "include" });
  if (!res.ok)
    throw new Error(`Knowledge base '${id}' not found: ${res.statusText}`);
  return res.json() as Promise<KnowledgeBase>;
}

export async function createKnowledgeBase(
  request: CreateKnowledgeBaseRequest,
): Promise<KnowledgeBase> {
  const res = await fetch(BASE(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to create knowledge base: ${res.statusText}`,
    );
  }
  return res.json() as Promise<KnowledgeBase>;
}

export async function updateKnowledgeBase(
  id: string,
  request: UpdateKnowledgeBaseRequest,
): Promise<KnowledgeBase> {
  const res = await fetch(`${BASE()}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to update knowledge base: ${res.statusText}`,
    );
  }
  return res.json() as Promise<KnowledgeBase>;
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  const res = await fetch(`${BASE()}/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to delete knowledge base: ${res.statusText}`);
}

export async function listDocuments(kbId: string): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${BASE()}/${kbId}/documents`, {
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to load documents: ${res.statusText}`);
  return res.json() as Promise<KnowledgeDocument[]>;
}

export async function uploadDocument(
  kbId: string,
  file: File,
): Promise<KnowledgeDocument> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE()}/${kbId}/documents`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to upload document: ${res.statusText}`,
    );
  }
  return res.json() as Promise<KnowledgeDocument>;
}

export async function deleteDocument(
  kbId: string,
  docId: string,
): Promise<void> {
  const res = await fetch(`${BASE()}/${kbId}/documents/${docId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to delete document: ${res.statusText}`);
}

export async function searchKnowledgeBase(
  kbId: string,
  query: string,
  topK = 5,
): Promise<SearchResult[]> {
  const res = await fetch(`${BASE()}/${kbId}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  const data = (await res.json()) as { results: SearchResult[] };
  return data.results;
}
