"use client";

import { UploadIcon } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { useUploadDocument } from "@/core/knowledge/hooks";
import { cn } from "@/lib/utils";

export function DocumentUpload({ kbId }: { kbId: string }) {
  const uploadMutation = useUploadDocument(kbId);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      for (const file of Array.from(files)) {
        try {
          await uploadMutation.mutateAsync(file);
          toast.success(`Uploaded "${file.name}"`);
        } catch (err) {
          toast.error(
            err instanceof Error
              ? err.message
              : `Failed to upload "${file.name}"`,
          );
        }
      }
      if (inputRef.current) inputRef.current.value = "";
    },
    [uploadMutation],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      void handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 transition-colors",
        isDragging
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-muted-foreground/50",
        uploadMutation.isPending && "pointer-events-none opacity-60",
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <UploadIcon className="text-muted-foreground size-8" />
      <div className="text-center">
        <p className="text-sm font-medium">
          {uploadMutation.isPending
            ? "Uploading..."
            : "Drop files here or click to upload"}
        </p>
        <p className="text-muted-foreground text-xs">
          PDF, TXT, MD, DOCX supported
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        multiple
        accept=".pdf,.txt,.md,.docx,.doc,.csv,.html"
        onChange={(e) => void handleFiles(e.target.files)}
      />
    </div>
  );
}
