"use client";

import { BookOpenIcon, FileTextIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { KnowledgeBase } from "@/core/knowledge/types";
import { cn } from "@/lib/utils";

export function KbCard({ knowledgeBase }: { knowledgeBase: KnowledgeBase }) {
  return (
    <Card
      className={cn(
        "hover:border-primary/40 cursor-pointer transition-colors",
      )}
    >
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-lg">
            <BookOpenIcon className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle className="truncate text-sm">
              {knowledgeBase.name}
            </CardTitle>
            <CardDescription className="line-clamp-2 text-xs">
              {knowledgeBase.description || "No description"}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-muted-foreground flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1">
            <FileTextIcon className="size-3" />
            {knowledgeBase.document_count ?? 0}{" "}
            {(knowledgeBase.document_count ?? 0) === 1 ? "document" : "documents"}
          </span>
          <span>
            {new Date(knowledgeBase.created_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
