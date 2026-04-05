import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  buildIndex,
  createKnowledgeBase,
  deleteDocument,
  deleteKnowledgeBase,
  getKnowledgeBase,
  keywordSearch,
  listDocuments,
  listKnowledgeBases,
  searchKnowledgeBase,
  uploadDocument,
} from "./api";
import type { CreateKnowledgeBaseRequest } from "./types";

export function useKnowledgeBases() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: () => listKnowledgeBases(),
  });
  return { knowledgeBases: data ?? [], isLoading, error };
}

export function useKnowledgeBase(id: string | null | undefined) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["knowledge-bases", id],
    queryFn: () => getKnowledgeBase(id!),
    enabled: !!id,
  });
  return { knowledgeBase: data ?? null, isLoading, error };
}

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateKnowledgeBaseRequest) =>
      createKnowledgeBase(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteKnowledgeBase(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useDocuments(kbId: string | null | undefined) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["knowledge-bases", kbId, "documents"],
    queryFn: () => listDocuments(kbId!),
    enabled: !!kbId,
  });
  return { documents: data ?? [], isLoading, error };
}

export function useUploadDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(kbId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId, "documents"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId],
      });
      void queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useDeleteDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => deleteDocument(kbId, docId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId, "documents"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId],
      });
      void queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

export function useSearchKnowledgeBase(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      searchKnowledgeBase(kbId, query, topK),
    onSuccess: (_data, { query }) => {
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId, "search", query],
      });
    },
  });
}

export function useBuildIndex(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => buildIndex(kbId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId, "documents"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["knowledge-bases", kbId],
      });
    },
  });
}

export function useKeywordSearch(kbId: string) {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      keywordSearch(kbId, query, topK),
  });
}
