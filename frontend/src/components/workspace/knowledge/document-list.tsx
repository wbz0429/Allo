"use client";

import { FileTextIcon, Trash2Icon } from "lucide-react";
import { useCallback } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDeleteDocument } from "@/core/knowledge/hooks";
import type { KnowledgeDocument } from "@/core/knowledge/types";

const STATUS_VARIANT: Record<
  KnowledgeDocument["status"],
  "default" | "secondary" | "destructive"
> = {
  processing: "secondary",
  ready: "default",
  error: "destructive",
};

export function DocumentList({
  kbId,
  documents,
  isLoading,
}: {
  kbId: string;
  documents: KnowledgeDocument[];
  isLoading: boolean;
}) {
  const deleteMutation = useDeleteDocument(kbId);

  const handleDelete = useCallback(
    async (docId: string, filename: string) => {
      if (!confirm(`Delete "${filename}"?`)) return;
      try {
        await deleteMutation.mutateAsync(docId);
        toast.success(`Deleted "${filename}"`);
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : "Failed to delete document",
        );
      }
    },
    [deleteMutation],
  );

  if (isLoading) {
    return (
      <div className="text-muted-foreground py-4 text-center text-sm">
        Loading documents...
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-muted-foreground py-4 text-center text-sm">
        No documents uploaded yet
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium">
        Documents ({documents.length})
      </h3>
      <div className="divide-y rounded-lg border">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center gap-3 px-4 py-3"
          >
            <FileTextIcon className="text-muted-foreground size-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{doc.filename}</p>
              <p className="text-muted-foreground text-xs">
                {doc.chunk_count} chunks &middot;{" "}
                {new Date(doc.created_at).toLocaleDateString()}
              </p>
            </div>
            <Badge variant={STATUS_VARIANT[doc.status]}>{doc.status}</Badge>
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive hover:text-destructive size-8"
              onClick={() => void handleDelete(doc.id, doc.filename)}
              disabled={deleteMutation.isPending}
              aria-label={`Delete ${doc.filename}`}
            >
              <Trash2Icon className="size-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
